import json

def safe_get(data, keys, default=None):
    """
    중첩 딕셔너리에서 키 체인을 따라 안전하게 값을 가져옵니다.
    """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
            if data == default:
                return default
        else:
            return default
    return data

class RouteExtractor:
    """
    SILS와 ISILS JSON 데이터에서 Safe Route, Base Route, Own Ship, Target Ships 정보를 추출하는 클래스.
    """
    def __init__(self, sils_json_data, isils_json_data):
        self.base_route = self.extract_base_route(sils_json_data)
        self.sils_safe_paths = self.extract_safe_path_at_event(sils_json_data)
        self.isils_safe_paths = self.extract_safe_path_at_event(isils_json_data)
        self.sils_target_ships_event_info = self.extract_target_ships_event_info(sils_json_data)
        self.isils_target_ships_event_info = self.extract_target_ships_event_info(isils_json_data)
        self.sils_own_ship_event_info = self.extract_own_ship_event_info(sils_json_data)
        self.isils_own_ship_event_info = self.extract_own_ship_event_info(isils_json_data)

        self.sils_own_ship_info = self.extract_own_ship_static_info(sils_json_data)
        self.isils_own_ship_info = self.extract_own_ship_static_info(isils_json_data)

        self.sils_event_data = self.extract_event_data(sils_json_data)
        self.is_path_gen_fail_sils, self.is_near_target_sils = self.extract_extract_evaluate_data(sils_json_data)

        self.isils_event_data = self.extract_event_data(isils_json_data)
        self.is_path_gen_fail_isils, self.is_near_target_isils = self.extract_extract_evaluate_data(isils_json_data)




    def flatten(self, item):
        """
        재귀적으로 리스트를 평탄화하여 모든 중첩을 풀어준다.
        예: [[a, b], c, [d, [e, f]]] => [a, b, c, d, e, f]
        """
        if isinstance(item, list):
            result = []
            for sub in item:
                result.extend(self.flatten(sub))
            return result
        else:
            return [item]

    def extract_safe_path_at_event(self, data):
        """
        Safe Route 추출 (cagaData → eventData → safe_path_info → route)
        여러 eventData가 있을 경우, 각 이벤트의 safe_path_info의 route를 리스트에 담아 반환.
        반환 예: [ route_event0, route_event1, ... ]
        """
        event_data = safe_get(data, ["cagaData", "eventData"], default=[])
        routes = []
        if isinstance(event_data, list):
            for event in event_data:
                route = safe_get(event, ["safe_path_info", "route"])
                if route is not None:
                    routes.append(route)
        return routes

    def extract_target_ships_event_info(self, data):
        """
        Target Ships 추출.
        각 event의 targetShips 데이터를 추출하여 리스트에 담아 반환.
        반환 예: [ targets_event0, targets_event1, ... ]
        """
        event_data = safe_get(data, ["cagaData", "eventData"], default=[])
        targets = []
        if isinstance(event_data, list):
            for event in event_data:
                tships = safe_get(event, ["timeSeriesData", "targetShips"], default=[])
                # 만약 tships가 리스트가 아니라면 리스트로 변환
                if not isinstance(tships, list):
                    tships = [tships]
                tships = self.flatten(tships)
                targets.append(tships)
        return targets

    def extract_base_route(self, data):
        """
        Base Route 추출 (trafficSituation → ownShip → waypoints)
        """
        return safe_get(data, ["trafficSituation", "ownShip", "waypoints"], default=[])

    def extract_own_ship_event_info(self, data):
        """
        Own Ship 정보 추출 (cagaData → eventData → timeSeriesData → ownShip)
        여러 eventData가 있을 경우, 각 이벤트의 timeSeriesData의 ownShip 정보를 리스트에 담아 반환.
        반환 예: [ ownShip_event0, ownShip_event1, ... ]
        """
        event_data = safe_get(data, ["cagaData", "eventData"], default=[])
        own_ships = []
        if isinstance(event_data, list):
            for event in event_data:
                own_ship = safe_get(event, ["timeSeriesData", "ownShip"])
                if own_ship is not None:
                    own_ships.append(own_ship)
        return own_ships
    
    def extract_own_ship_static_info(self, data):
        return safe_get(data, ["trafficSituation", "ownShip", "static"], default={})
    
    def extract_event_data(self, data):
        return safe_get(data, ["cagaData", "eventData"], default=[])
    

    def extract_extract_evaluate_data(self, data):
        event_data = safe_get(data, ["cagaData", "eventData"], default=[])
        path_gens = []
        near_targets = []

        if isinstance(event_data, list):
            for event in event_data:
                path_gen = safe_get(event, ["caPathGenFail"])
                near_target = safe_get(event, ["isNearTarget"])
                if path_gen is not None and near_target is not None:
                    path_gens.append(path_gen)
                    near_targets.append(near_target)

        return path_gens, near_targets
