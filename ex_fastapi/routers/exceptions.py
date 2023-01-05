class ItemNotFound(Exception):
    pass


class NotUnique(Exception):
    fields: list[str]

    def __init__(self, *args, fields: list[str] = None):
        super().__init__(*args)
        self.fields = fields or []
