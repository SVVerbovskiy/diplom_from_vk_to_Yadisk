import requests
from datetime import datetime
import configparser
from tqdm import tqdm
import json
from art import tprint

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("config.ini")  # читаем конфиг



def time_converter(unix_time):
    """Преобразование даты из формата unix в YYYY-MM-DD HH:MM:SS"""
    unix_val = datetime.fromtimestamp(unix_time)
    str_time = unix_val.strftime('%Y-%m-%d time %H-%M-%S')
    return str_time


def max_dpi(search_dict):
    """Функция возвращает ссылку на фото самого большого размера"""
    max_size = 0
    need_value = 0
    for i in range(len(search_dict)):
        file_size = search_dict[i].get('width') * search_dict[i].get('height')
        if file_size > max_size:
            max_size = file_size
            need_value = i
    return search_dict[need_value].get('url'), search_dict[need_value].get('type')


class VK:
    def __init__(self, token, version='5.131'):
        """Метод для получения начальных параметров запроса для VK"""
        self.token = config["VK"]["TOKEN"]
        self.id = config["VK"]["ID"]
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}
        self.json, self.export_dict = self._sort_info()

    def _get_photo_info(self):
        """Метод для получения количества фотографий и массива фотографий"""
        URL = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': self.id,
                  'album_id': 'profile',
                  'photo_sizes': 1,
                  'extended': 1,
                  'rev': 1,
                  'count': 1000
                  }
        res = requests.get(URL, params={**self.params, **params}).json()['response']
        return res['count'], res['items']

    def _get_logs_only(self):
        """Метод для получения словаря с параметрами фотографий"""
        photo_count, photo_items = self._get_photo_info()
        result = {}
        for i in range(photo_count):
            likes_count = photo_items[i]['likes']['count']
            url_download, picture_size = max_dpi(photo_items[i]['sizes'])
            time_warp = time_converter(photo_items[i]['date'])
            new_value = result.get(likes_count, [])
            new_value.append({'likes_count': likes_count,
                              'add_name': time_warp,
                              'url_picture': url_download,
                              'size': picture_size})
            result[likes_count] = new_value
        return result

    def _sort_info(self):
        """Метод для получения словаря с параметрами фотографий и списка JSON для выгрузки"""
        json_list = []
        sorted_dict = {}
        picture_dict = self._get_logs_only()
        counter = 0
        for elem in picture_dict.keys():
            for value in picture_dict[elem]:
                if len(picture_dict[elem]) == 1:
                    file_name = f'{value["likes_count"]}.jpeg'
                else:
                    file_name = f'{value["likes_count"]} {value["add_name"]}.jpeg'
                json_list.append({'file name': file_name, 'size': value["size"]})
                if value["likes_count"] == 0:
                    sorted_dict[file_name] = picture_dict[elem][counter]['url_picture']
                    counter += 1
                else:
                    sorted_dict[file_name] = picture_dict[elem][0]['url_picture']
        return json_list, sorted_dict


class Yandex:
    def __init__(self, folder_name, token_list, num=5):
        """Метод для получения основных параметров для загрузки фотографий на Я-диск"""
        self.token = config["YD"]["TOKEN"]
        self.added_files_num = num
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.headers = {'Authorization': self.token}
        self.folder = self._create_folder(folder_name)

    def _create_folder(self, folder_name):
        """Метод для создания папки на Я-диске для загрузки фотографий"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        if requests.get(url, headers=self.headers, params=params).status_code != 200:
            requests.put(url, headers=self.headers, params=params)
            print(f'\nПапка {folder_name} успешно создана в корневом каталоге Яндекс диска\n')
        else:
            print(f'\nПапка {folder_name} уже существует. Файлы с одинаковыми именами не будут скопированы\n')
        return folder_name

    def _in_folder(self, folder_name):
        """Метод для получения ссылки для загрузки фотографий на Я-диск"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        resource = requests.get(url, headers=self.headers, params=params).json()['_embedded']['items']
        in_folder_list = []
        for elem in resource:
            in_folder_list.append(elem['name'])
        return in_folder_list

    def create_copy(self, dict_files):
        """Метод загрузки фотографий на Я-диск"""
        files_in_folder = self._in_folder(self.folder)
        copy_counter = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.added_files_num))):
            if copy_counter < self.added_files_num:
                if key not in files_in_folder:
                    params = {'path': f'{self.folder}/{key}',
                              'url': dict_files[key],
                              'overwrite': 'false'}
                    requests.post(self.url, headers=self.headers, params=params)
                    copy_counter += 1
                else:
                    print(f'Внимание:Файл {key} уже существует')
            else:
                break

        print(f'\nЗапрос завершен, новых файлов скопировано (по умолчанию: 5): {copy_counter}'
              f'\nВсего файлов в исходном альбоме VK: {len(dict_files)}')


if __name__ == '__main__':
    tprint('From VK to YandexDisk')

    config['VK']['ID'] = input('Введите id пользователя: ')
    config["YD"]["TOKEN"] = input('Токен с Полигона Яндекс Диска: ')

    tokenVK = config["VK"]["TOKEN"]  # токен и id доступа хранятся в файле config.ini
    tokenYandex = config["YD"]["TOKEN"]  # токен хранится в файле config.ini

    my_VK = VK(tokenVK)  # Получение JSON списка с информацией о фотографиях

    with open('my_VK_photo.json', 'w') as outfile:  # Сохранение JSON списка ф файл my_VK_photo.json
        json.dump(my_VK.json, outfile)

    # Создаем экземпляр класса Yandex с параметрами: "Имя папки", "Токен" и количество скачиваемых файлов
    my_yandex = Yandex('VK photo copies', tokenYandex, 5)
    my_yandex.create_copy(my_VK.export_dict)  # Вызываем метод create_copy для копирования фотографий с VK на Я-диск
