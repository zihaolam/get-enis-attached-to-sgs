from typing import Dict, List


def input_y_n(message, default="Y") -> bool:
    y_n = input(f"{message} Y/N: [{default}]").lower()
    while y_n != 'y' and y_n != 'n' and y_n != "":
        print("Invalid input, please select Y or N")
        y_n = input("Search for another? Y/N: [Y] ").lower()

    if y_n == "y" or y_n == "":
        return True

    return False


def filter_response(data: Dict[str, any], wanted_fields: List[str]) -> dict:
    return {key: value for key, value in data.items() if key in wanted_fields}
