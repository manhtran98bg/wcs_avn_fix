class Helper:
    @staticmethod
    def extractDict(
            data: dict, only_need: list = None, must_have: list = None,
            strict: bool = True, default = None):
        """
        Extract data in dictionary

        only_need: remove keys other than these (even if these keys not exist)
        must_have: strictly require
        (raise Exception when fail to match if strict, else return default)

        Return: extracted dict
        """
        new_data = {}
        if only_need:
            for key in data:
                if key in only_need:
                    new_data[key] = data[key]
        else:
            new_data = data.copy()

        if must_have:
            for key in must_have:
                if key not in new_data:
                    if strict:
                        raise Exception(f"No key in dict ({key}, {new_data})")
                    else:
                        new_data[key] = default
        
        return new_data