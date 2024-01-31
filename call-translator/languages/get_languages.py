import json


def __get_file_path(filename: str = 'languages.json'):
    return f'{'/'.join(__file__.split('/')[:-1])}/{filename}'


def __get_languages():
    with open(__get_file_path(), 'r') as file:
        return json.load(file)


def __get_names():
    _names = []
    for code in languages[tuple(languages.keys())[0]]:
        data = code[tuple(code.keys())[0]]
        _names.append({data[tuple(data.keys())[0]]: tuple(data.keys())[0]})

    return _names


languages = __get_languages()
names = __get_names()


def get_language(name: str, service: str):
    service_languages = languages[service]
    for data in service_languages:
        for c, d in data.items():
            for code in d.keys():
                if d[code] == name:
                    return code


# print(get_language('English', service='deepl'))


