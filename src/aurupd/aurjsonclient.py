import requests
from aurupd.aurpackage import AurPackage

class AurJsonClient:
    def __init__(self):
        self.target_url: str = "https://aur.archlinux.org/rpc/v5"

    def search_by(self, search: str, by: str) -> list[AurPackage] | None:
        search_url = f"{self.target_url}/search/{search}?by={by}"

        response = requests.get(search_url)
        res_json = response.json()

        if res_json["resultcount"] == 0:
            return None

        return [AurPackage(name=package["Name"], description=package["Description"]) for package in res_json["results"]]

    def get_single_package(self, package: str) -> AurPackage | None:
        search_url = f"{self.target_url}/info/{package}"

        response = requests.get(search_url)
        res_json = response.json()

        if res_json["resultcount"] == 0:
            return None

        return AurPackage(name=res_json["results"][0]["Name"], description=res_json["results"][0]["Description"])

    def search_by_user(self, user: str):
        by_maintainer = self.search_by(user, "maintainer")
        by_comaintainers = self.search_by(user, "comaintainers")

        result: list[AurPackage] = []

        if by_maintainer:
            result = [*result, *by_maintainer]

        if by_comaintainers:
            result = [*result, *by_comaintainers]

        return result