import re


class MarkdownLoader:
    VAR_EXPR = r"{{(.*?)}}"
    COMMENT_EXPR = r"{::comment}.*?{:/comment}"

    def __init__(self, filepath, **vars):
        self.raw_data = self.load(filepath)
        self.update(**vars)

    def __str__(self):
        return self.data

    def update(self, **vars):
        self.data = self.parse(self.raw_data, **vars)

    @staticmethod
    def load(filepath):
        with open(filepath) as f:
            data = f.read()

        return data

    @classmethod
    def parse(cls, template, **data):
        template = cls.remove_comments(template)
        variables = cls.inspect(template)
        missing_vars = variables - data.keys()

        if missing_vars:
            raise ValueError(f"Missing variables in data: {', '.join(missing_vars)}")

        def replace_match(match):
            variable = match.group(1)
            return str(data[variable])

        pattern = re.compile(cls.VAR_EXPR)
        return pattern.sub(replace_match, template)

    @classmethod
    def remove_comments(cls, template):
        comment_pattern = re.compile(cls.COMMENT_EXPR, re.DOTALL)
        cleaned_template = comment_pattern.sub("", template).strip()

        # Remove blank lines left over by any removed comments
        cleaned_template = re.sub(r"\n\s*\n", "\n\n", cleaned_template)
        return cleaned_template

    @classmethod
    def inspect(cls, template):
        pattern = re.compile(cls.VAR_EXPR)
        return set(pattern.findall(template))
