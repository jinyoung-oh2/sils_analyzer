import json
from loguru import logger
from collections import defaultdict
import os
import csv

class MaritimeSchemaOutputReader:
    def __init__(self, folder_path: str, output_csv_path: str):
        self.folder_path = folder_path
        self.output_csv_path = output_csv_path
        self.summaries = []
        try:
            self.file_paths = [
                os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.json')
            ]
        except FileNotFoundError:
            logger.error(f"Folder not found: {folder_path}")
            self.file_paths = []

    def extract_event_summary(self, data):
        """Extract event data from cagaData."""
        event_data_list = []
        event_data = data.get('cagaData', {}).get('eventData', [])

        for event in event_data:
            event_info = {
                "time": event.get("time", None),
                "caPathGenFail": event.get("caPathGenFail", None),
                "isNearTarget": event.get("isNearTarget", None),
                "safe_path_info": defaultdict
            }

            safe_path_info = event.get("safe_path_info", {})
            route = safe_path_info.get("route", [])
            if route:
                event_info["safe_path_info"] = {
                    "waypoint_number": len(route) if isinstance(route, list) else 0,
                    "travelTime": safe_path_info.get("travelTime", 0),
                    "travelDistance": safe_path_info.get("travelDistance", 0),
                    "maxCourseChange": safe_path_info.get("maxCourseChange", 0),
                    "maxXTEFromGlobalPath": safe_path_info.get("maxXTEFromGlobalPath", 0)
                }
            else:
                event_info["safe_path_info"] = {
                    "waypoint_number": 0,
                    "travelTime": safe_path_info.get("travelTime", 0),
                    "travelDistance": safe_path_info.get("travelDistance", 0),
                    "maxCourseChange": safe_path_info.get("maxCourseChange", 0),
                    "maxXTEFromGlobalPath": safe_path_info.get("maxXTEFromGlobalPath", 0)
                }

            event_data_list.append(event_info)
        return event_data_list
    
    def extract_configuration(self, data):
        """Extract configuration data from cagaData and trafficSituation."""
        try:
            caga_data = data.get('cagaData', {})
            return {
                "version": caga_data.get('caga_configuration', {}).get('version', None),
                "number_of_target": len(data['trafficSituation'].get('targetShips', [])),
                "ownship_speed": data['trafficSituation'].get('ownShip', {}).get('initial', {}).get('sog', None),
                "sea_state": caga_data.get('caga_configuratio**', {}).get('sils_user_setting', {}).get('sea_state', None),
                "is_dynamic": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('is_dynamic', None),
                "target_course_change_range": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('target_course_change_range', None),
                "target_speed_change_range": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('target_speed_change_range', None),
                "target_minimum_speed": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('target_minimum_speed', None),
                "target_maximum_speed": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('target_maximum_speed', None),
                "target_minimum_bearing": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('target_minimum_bearing', None),
                "target_maximum_bearing": caga_data.get('caga_configuration', {}).get('sils_user_setting', {}).get('target_maximum_bearing', None),
                "CPA": caga_data.get('caga_configuration', {}).get('hinas_setup', {}).get('CPA', None),
                "TCPA_GW": caga_data.get('caga_configuration', {}).get('hinas_setup', {}).get('TCPA_GW', None),
                "TCPA_SO": caga_data.get('caga_configuration', {}).get('hinas_setup', {}).get('TCPA_SO', None),
                "Minimum_range_of_interest": caga_data.get('caga_configuration', {}).get('hinas_setup', {}).get('Minimum_range_of_interest', None),
                "ROT_in_return": caga_data.get('caga_configuration', {}).get('ROT_in_return', None),
                "ROT_in_evasion": caga_data.get('caga_configuration', {}).get('ROT_in_evasion', None),
                "user_selection_time": 3,
                "Time": data.get('creationTime', None)
            }
        except (KeyError, TypeError):
            logger.error("Configuration data missing or malformed.")
            return {}
    

    def generate_summary(self, file_path):
        """Generate a summary of extracted data."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error(f"Error reading file: {file_path}")
            return {}

        event_data = self.extract_event_summary(data)
        config_summary = self.extract_configuration(data)

        # Safe path information
        waypoint_number_max = 0
        travel_time_max = 0
        travel_distance_max = 0
        path_update_number = 0
        isSafePathGenerationFailed = False
        isNearTarget = False
        time = ""
        for event in event_data:
            safe_path_info = event.get("safe_path_info", {})
            waypoint_number = safe_path_info.get("waypoint_number", 0)
            travelTime = safe_path_info.get("travelTime", 0)
            travelDistance = safe_path_info.get("travelDistance", 0)
            waypoint_number_max = max(waypoint_number_max, waypoint_number)
            travel_time_max = max(travel_time_max, travelTime)
            travel_distance_max = max(travel_distance_max, travelDistance)
            if safe_path_info:
                path_update_number += 1
            # ODD
            if event.get("caPathGenFail", None) == True:
                isSafePathGenerationFailed = True
            if event.get("isNearTarget", None) == True:
                isNearTarget = True
            time = event.get("time", None)

        # Make summary
        event_summary =  {
            "time": time,
            "isSafePathGenerationFailed": isSafePathGenerationFailed,
            "isNearTarget": isNearTarget,
            "waypoint_number_max": waypoint_number_max,
            "travel_time_max": travel_time_max,
            "travel_distance_max": travel_distance_max,
            "path_update_number": path_update_number
        }
        config_summary = self.extract_configuration(data)

        summary = event_summary.copy()
        summary.update(config_summary)
        summary["scenario name"] = os.path.splitext(os.path.basename(file_path))[0]
        return summary

    def process_all_files(self):
        """Process all JSON files in the folder and generate summaries."""
        for file_path in self.file_paths:
            summary = self.generate_summary(file_path)
            if summary:
                self.summaries.append(summary)
        return self.summaries

    def save_to_csv(self):
        """Save summaries to a CSV file."""
        if not self.summaries:
            logger.error("No summaries to save. Run process_all_files first.")
            return

        # Define the CSV columns based on summary keys
        fieldnames = [
            "version", "scenario name", "number_of_target", "ownship_speed", "sea_state", "is_dynamic",
            "target_course_change_range", "target_speed_change_range", "target_minimum_speed", "target_maximum_speed",
            "target_minimum_bearing", "target_maximum_bearing", "user_selection_time", "CPA", "TCPA_GW", "TCPA_SO",
            "Minimum_range_of_interest", "ROT_in_return", "ROT_in_evasion", "Time", "waypoint_number_max",
            "travel_time_max", "travel_distance_max", "path_update_number", "isNearTarget", "isSafePathGenerationFailed"
        ]

        # Write to CSV
        try:
            with open(self.output_csv_path, mode='w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for summary in self.summaries:
                    filtered_summary = {key: summary.get(key, None) for key in fieldnames}
                    writer.writerow(filtered_summary)
            logger.info(f"Summaries saved to {self.output_csv_path}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")


def run_maritimeschema_output_reader(folder_path: str, output_csv_path: str):
    """Main function to process maritime schema output and save to CSV."""
    reader = MaritimeSchemaOutputReader(folder_path, output_csv_path)
    reader.process_all_files()
    reader.save_to_csv()

if __name__ == "__main__":
    # Example usage
    folder_path = "output/2025-02-10 04:56:56.934941"
    output_csv_path = "output/maritimeschema_output_reader_test.csv"
    run_maritimeschema_output_reader(folder_path, output_csv_path)
