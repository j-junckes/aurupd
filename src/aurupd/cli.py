#!/usr/bin/env python3

import argparse
from termcolor import colored

from aurpackage import AurPackage
from aurjsonclient import AurJsonClient
from istool import is_tool

def main():
    parser = argparse.ArgumentParser(description="AUR package updater")
    group = parser.add_argument_group("Search for packages by maintainer or specific package")
    exclusive_group = group.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument("--search", type=str, help="Username of maintainer or comaintainer")
    exclusive_group.add_argument("--package", type=str, help="Name of the package")
    parser.add_argument("--update", action="store_true", help="Update the packages")
    parser.add_argument("--email", type=str, help="Email to use for git")
    parser.add_argument("--name", type=str, help="Name to use for git")
    parser.add_argument("--commit", type=str, help="Commit message to use for git", default="Update to new version")

    args = parser.parse_args()

    if not is_tool("git"):
        print(colored("Git is not installed. Please install git.", "red"))
        return

    if not is_tool("makepkg"):
        print(colored("makepkg is not installed. Please install makepkg.", "red"))
        return

    aur_client = AurJsonClient()

    packages: list[AurPackage] = aur_client.search_by_user(args.search) if args.search else [aur_client.get_single_package(args.package)]

    if args.search and not packages:
        print(f"No packages found for user {args.search}")
        return

    if not args.search and not packages:
        print(f"No package found for {args.package}")
        return

    if args.search:
        print(f"Found {len(packages)} packages for user {args.search}")
    else:
        print(f"Found package {packages[0].name}")

    for package in packages:
        print(f"\t- {package.name}")

    print("")

    print("Downloading packages...")

    for package in packages:
        print(f"\t- {colored(package.name, attrs=["bold"])}...")
        package.init_package()
        if package.needs_update():
            print(colored(f"\t\t- {package.name} - {package.version} has a new version: {package.new_version}",
                          "light_yellow", attrs=["bold"]))
        else:
            print(colored(f"\t\t- {package.name} - {package.version} is up to date", "light_green"))

    if not args.update:
        return

    print("")

    print("Updating packages...")

    for package in packages:
        if package.needs_update():
            print(f"\t- {colored(package.name, attrs=['bold'])}...")
            package.update_package(args.email, args.name, args.commit)
            print(colored(f"\t\t- {package.name} updated to {package.new_version}",
                          "light_green", attrs=["bold"]))


if __name__ == "__main__":
    main()
