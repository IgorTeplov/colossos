Для початку роботи вам потрібно:

1. Мати ssh доступ до серверу через ключ
2. Створити локально папку у якій буде знаходитись копія серверної папки яку потрібно синхронізувати
3. У цій папці створити файл .colossos.cfex
4. Заповнити цей файл наступним шаблоном:

SSH_KEY = /path/to/your/ssh/key

SSH_USER = root

SSH_HOST = 127.0.0.1

LOCAL_DIR = /path/to/your/dir/with/this/file

REMOTE_DIR = /path/to/dir/that/need/sunc/on/server

5. Синхронізувати папки командою

python colossos -d /path/to/your/dir/with/this/file -s

6. -s є опціональним флагом який завантажує всі файли з потрібної папки на сервері у локальну

Для запуску використовуйте цю команду
python colossos -d /path/to/your/dir/with/this/file

Шалених вам пригод! ;)
