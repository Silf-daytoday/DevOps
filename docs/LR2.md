# ЛР2. Развертывание в Linux без контейнеров

Приложение варианта 8: Flask + PostgreSQL 16, версия разработки `0.2.0-dev`.
Интерфейс и API ЛР1 сохранены. Старый `v0.1.0` остается историей ЛР1.
Ниже — команды для ручного выполнения. Наличие инструкции не означает, что
серверные проверки уже выполнены.

## 1. Пример адресов и исходное состояние

Все адреса 192.0.2.x ниже — условные примеры для документации, не реальные
адреса учебного стенда. Перед выполнением команд замените их своими адресами,
а devopsadmin и Student — своими именами пользователей. Реальные настройки
передавайте во внешнем env; не публикуйте их в Git.

| Узел | Адрес | Имя |
| --- | --- | --- |
| Windows 10, VMnet1 Host-only | 192.0.2.1/24 | рабочее место |
| Ubuntu app-server | 192.0.2.10/24 | app-server |
| Ubuntu db-server | 192.0.2.20/24 | db-server |

Администратор обеих ВМ: `devopsadmin`.
Системный пользователь приложения `devopsapp` отличается от роли PostgreSQL
`devops_app`. Серверы без GUI, целевой режим `multi-user.target`.
NAT `ens33` дает интернет; Host-only `ens34` — связь между узлами.
Host-only сеть без gateway/DNS. Статический адрес не зависит от NAT DHCP.

**Уже сделано в текущем окружении:** установка Ubuntu Server, сеть, SSH по ключу,
запрет root/парольного SSH, установка PostgreSQL 16, база `devops`, роли
`devops_owner`/`devops_app`, CONNECT/USAGE без CREATE, сетевой доступ с app-server,
UFW db-server. Пароль `devops_app` уже задан. Таблицы еще нужно применить.
Доступ к PostgreSQL с app-server проверен; права CREATE — false.

**Еще нужно:** применить схему/права, подготовить отдельную тестовую БД, проверить
код, установить приложение, настроить env/systemd/UFW app-server, выполнить защиту.

## 2. Получение исходников

### PowerShell Windows

Если feature-ветка уже опубликована:

```powershell
git clone --branch feature/lr2-postgresql-linux https://github.com/Silf-daytoday/DevOps.git DevOps-LR2
cd DevOps-LR2
```

Если получен архив исходников до публикации — распакуйте его в отдельную папку,
например `C:\Users\Student\DevOps-LR2`, и перейдите в нее. Не накладывайте архив
на незакоммиченные изменения старой рабочей копии.

В папке проекта соберите исходники без env, Git и venv:

```powershell
tar -czf lr2-source.tar.gz app.py check.py schema.sql requirements.txt Makefile .env.example deploy docs README.md
scp -i "$env:USERPROFILE\.ssh\devops_lr2" lr2-source.tar.gz devopsadmin@192.0.2.10:/tmp/lr2-source.tar.gz
scp -i "$env:USERPROFILE\.ssh\devops_lr2" lr2-source.tar.gz devopsadmin@192.0.2.20:/tmp/lr2-source.tar.gz
```

Приватный ключ остается на Windows. Не переносите его на серверы.

### SSH app-server

```bash
mkdir -p ~/devops-work
tar -xzf /tmp/lr2-source.tar.gz -C ~/devops-work
cd ~/devops-work
sudo apt update
sudo apt install -y python3 python3-venv make postgresql-client-16 ufw
```

Это пользовательская рабочая папка. Установленная служба будет читать код из
другого места — `/opt/devops/app`.

### SSH db-server

Каталог администраторского home может быть недоступен пользователю postgres,
поэтому SQL размещаем в отдельном каталоге. В архиве нет секретов:

```bash
sudo install -d -o root -g root -m 0755 /var/tmp/devops-lr2
sudo tar -xzf /tmp/lr2-source.tar.gz -C /var/tmp/devops-lr2 --no-same-owner
```

## 3. Схема и права основной базы

### SSH db-server — продолжение уже настроенного окружения

Роли и база уже существуют. **Не запускайте `00-create-database.sql` повторно.**

```bash
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -f /var/tmp/devops-lr2/deploy/01-apply-schema.sql
```

Скрипт подключается к `devops`, создает таблицы от имени `devops_owner`,
выдает `devops_app` только SELECT/INSERT на таблицы и USAGE на последовательности.
Роль приложения не получает CREATE, UPDATE, DELETE, TRUNCATE и владение объектами.

Повторный запуск не удаляет данные. `CREATE TABLE IF NOT EXISTS` здесь — начальная
схема ЛР2, не система миграций и не средство изменения существующих столбцов.

Проверка владельцев (консоль PostgreSQL или команда ниже):

```bash
sudo -u postgres psql -d devops -c "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public';"
```

Должны быть шесть таблиц и владелец `devops_owner`.

## 4. Отдельная тестовая база

### SSH db-server

```bash
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -f /var/tmp/devops-lr2/deploy/02-test-database.sql
sudo -u postgres psql
```

### Консоль psql

```text
SET password_encryption = 'scram-sha-256';
\password devops_test
\q
```

Задайте отдельный пароль тестовой роли. Не публикуйте его.

### SSH db-server

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Добавьте один раз, сохранив локальные правила и правило основной базы:

```text
host    devops_test    devops_test    192.0.2.10/32    scram-sha-256
```

Сохранение nano: Ctrl+O, Enter, Ctrl+X.

```bash
sudo systemctl reload postgresql@16-main
```

Firewall менять не требуется: источник TCP 5432 по-прежнему только app-server.
Роль `devops_test` владеет своей тестовой базой; к основной базе она не имеет CONNECT
благодаря отзыву прав PUBLIC. Она не является superuser и не состоит в devops_owner.

### SSH app-server

```bash
cd ~/devops-work
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export DB_HOST=192.0.2.20
export DB_PORT=5432
export DB_NAME=devops_test
export DB_USER=devops_test
read -rsp 'Пароль devops_test: ' DB_PASSWORD
printf '\n'
export DB_PASSWORD
make verify
make verify
```

Оба запуска должны закончиться «ИТОГ: все проверки прошли.» и «syntax OK».
SECRET_KEY и пароль начального admin для проверок генерируются в памяти check.py,
если они не заданы. Это не настройки установленного приложения.

check.py сначала сверяет переменные DB_NAME/DB_USER, затем фактические
current_database()/current_user. Только после этого очищает все шесть тестовых
таблиц. Не запускайте проверки с пользовательскими данными в devops_test:
эта база целиком предназначена для тестов.

Безопасная проверка отказа, без подключения и очистки:

```bash
DB_NAME=devops DB_USER=devops_app python check.py
echo $?
```

Ожидаются «ОТКАЗ» и код 1. Основная база при этом не затрагивается.

После проверок:

```bash
unset DB_PASSWORD
deactivate
```

Если проверка не прошла — сохраните текст ошибки и исправьте причину.
Не убирайте проверки и не открывайте БД для Windows.

## 5. Установка приложения и внешней конфигурации

### SSH app-server

После успешных проверок:

```bash
cd ~/devops-work
sudo bash deploy/install-app.sh
sudo nano /etc/devops/app.env
```

Скрипт создает непривилегированного devopsapp, ставит код, venv и unit.
Он не запускает приложение, не меняет БД, SSH или firewall.
Существующий app.env сохраняется. При первом запуске туда копируется шаблон.

Заполните параметры:

```dotenv
DB_HOST=192.0.2.20
APP_HOST=192.0.2.10
DB_PORT=5432
DB_NAME=devops
DB_USER=devops_app
DB_PASSWORD=CHANGE_ME_DATABASE_PASSWORD
PORT=5000
APP_VERSION=0.2.0-dev
SECRET_KEY=CHANGE_ME_RANDOM_SESSION_SECRET
ADMIN_PASSWORD=CHANGE_ME_INITIAL_ADMIN_PASSWORD
```

APP_HOST — реальный Host-only IPv4 app-server; Gunicorn получает адрес через
EnvironmentFile, без зашитого адреса в unit.

Замените все CHANGE_ME-значения: DB_PASSWORD — уже заданный пароль devops_app,
SECRET_KEY — случайная длинная строка, ADMIN_PASSWORD — новый пароль веб-admin.
Для генерации секрета можно выполнить `python3 -c 'import secrets; print(secrets.token_hex(32))'`
и вставить результат в nano. Не присылайте настоящие значения в чат/коммиты.

Для env удобно использовать пароли из букв, цифр и знаков `-_!@.`.
Если значение содержит пробелы, заключайте его в кавычки по правилам systemd EnvironmentFile.
Внутри env не нужно писать `export`. Эти файлы не предназначены для автоматического
выполнения как shell-скрипты. Сервис читает их через EnvironmentFile.
Копирование .env само по себе ничего не загружает в Python.

```bash
sudo chmod 600 /etc/devops/app.env
sudo chown root:root /etc/devops/app.env
sudo systemctl enable --now devops-app
sudo systemctl status devops-app --no-pager
curl -i http://192.0.2.10:5000/health
curl http://192.0.2.10:5000/version
```

Стартует Gunicorn с двумя worker от devopsapp. ExecStartPre вызывает `flask --app app init-admin`.
Команда только создает admin, если его нет; таблицы не создает, пароль существующего
admin не меняет. Изменение ADMIN_PASSWORD в app.env не сбрасывает существующий пароль.

При недоступной БД во время старта init-admin завершится ошибкой;
systemd повторяет запуск через 5 секунд. StartLimitIntervalSec=0 оставляет повторные
попытки, в том числе когда ВМ базы включилась позже приложения.
network-online.target относится только к локальной сети, а не к готовности удаленной БД.

При проблемах:

```bash
sudo journalctl -u devops-app -n 60 --no-pager
```

Веб-адрес на Windows: http://192.0.2.10:5000/
Начальная учетная запись: admin и заданный вами ADMIN_PASSWORD.

## 6. Firewall app-server

### SSH app-server

Сначала разрешите SSH, затем включайте firewall. Старую SSH-сессию держите открытой
до успешной проверки нового соединения.

```bash
sudo ufw status numbered
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.0.2.1 to any port 22 proto tcp
sudo ufw allow from 192.0.2.1 to any port 5000 proto tcp
sudo ufw enable
sudo ufw status numbered
```

Если уже есть широкие разрешения на 22/5000, проверьте их и удалите только лишние
по фактическим номерам, затем снова покажите status. Не делайте безусловный ufw reset.

На db-server уже должны быть incoming deny, outgoing allow, TCP 22 только с .77.1
и TCP 5432 только с .77.10. Дополнительных разрешений для Windows на БД не требуется.

## 7. Права на файлы

### SSH app-server

```bash
id devopsapp
stat -c '%U:%G %a %n' /opt/devops/app /opt/devops/app/app.py /opt/devops/venv /etc/devops /etc/devops/app.env
sudo -u devopsapp test -r /opt/devops/app/app.py
sudo -u devopsapp test ! -w /opt/devops/app/app.py
sudo -u devopsapp test ! -r /etc/devops/app.env
```

Ожидается: код root:root 644, каталог кода 755; env-каталог root:root 750,
env-файл root:root 600. Последние три команды успешны и обычно ничего не печатают.
Systemd читает EnvironmentFile до запуска процесса от devopsapp; самому devopsapp
читать файл с диска не требуется. Код и установленный venv ему не принадлежат.
Для библиотек и бинарников venv нужен доступ чтения/прохода; стандартный umask установки 022.

## 8. Проверки защиты

Не отмечайте пункты выполненными до реального выполнения на ВМ.

### Службы, процесс, порт и журналы — SSH app-server

```bash
sudo systemctl is-enabled devops-app
sudo systemctl stop devops-app
sudo systemctl start devops-app
sudo systemctl restart devops-app
sudo systemctl status devops-app --no-pager
ps -u devopsapp -o user,pid,ppid,args
sudo ss -ltnp 'sport = :5000'
sudo journalctl -u devops-app -n 50 --no-pager
```

### Функциональность — браузер Windows

Откройте приложение, зарегистрируйтесь/войдите. Создайте группу, студента и дисциплину.
Попытка выставить оценку без плана отклоняется. Добавьте учебный план группы на семестр,
затем оценку 2–5; проверьте отчет. Оценка 10 и дубликаты отклоняются.
Перезапустите службу и убедитесь, что данные и вход продолжают работать.

### Аварийное завершение — SSH app-server

```bash
sudo systemctl show devops-app -p MainPID -p NRestarts
sudo systemctl kill --kill-whom=all --signal=SIGKILL devops-app
```

Подождите 5–10 секунд, затем:

```bash
sudo systemctl show devops-app -p MainPID -p NRestarts -p ActiveState
curl -i http://192.0.2.10:5000/health
```

Новый MainPID, выросший NRestarts, active и 200 подтверждают восстановление.
Обычный systemctl restart не заменяет этот опыт.

### Остановка БД

SSH db-server:

```bash
sudo systemctl stop postgresql@16-main
```

SSH app-server:

```bash
curl -i http://192.0.2.10:5000/health
sudo systemctl is-active devops-app
sudo journalctl -u devops-app -n 30 --no-pager
```

Ожидается HTTP 500, status=fail без внутренних ошибок в ответе;
Gunicorn остается активным, в журнале есть тип ошибки БД.

SSH db-server:

```bash
sudo systemctl start postgresql@16-main
pg_lsclusters
```

Снова /health на app-server — 200 без изменения кода.

### Изменение параметра службы и восстановление — SSH app-server

```bash
sudo mkdir -p /etc/systemd/system/devops-app.service.d
sudo nano /etc/systemd/system/devops-app.service.d/90-lr2-demo.conf
```

Вставьте:

```ini
[Service]
RestartSec=10s
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart devops-app
sudo systemctl show devops-app -p RestartUSec
```

Должно быть 10s. Затем удалите только созданный файл:

```bash
sudo rm /etc/systemd/system/devops-app.service.d/90-lr2-demo.conf
sudo systemctl daemon-reload
sudo systemctl restart devops-app
sudo systemctl show devops-app -p RestartUSec
```

Должно вернуться 5s.

### Сетевое ограничение БД

PowerShell Windows:

```powershell
Test-NetConnection 192.0.2.20 -Port 5432
```

Ожидается TcpTestSucceeded=False. Одновременно SSH app-server:

```bash
psql -h 192.0.2.20 -U devops_app -d devops -W -c "SELECT current_user, inet_client_addr(), inet_server_addr();"
psql -h 192.0.2.20 -U devops_app -d devops -W -c "SELECT has_database_privilege(current_user,current_database(),'CREATE') AS can_create_schema, has_schema_privilege(current_user,'public','CREATE') AS can_create_table;"
```

Подключение успешно, адрес клиента .77.10, оба CREATE — false.
SQL-проверка нужна одновременно с сетевой: выключенная БД не доказывает firewall.

### Перезагрузка

SSH db-server: `sudo systemctl is-enabled postgresql`, `sudo reboot`.
SSH app-server: `sudo systemctl is-enabled devops-app`, `sudo reboot`.
После восстановления обеих ВМ: SSH по ключам, `systemctl get-default` → multi-user.target,
`ip -br address` → прежние статические адреса, `pg_lsclusters` → online,
`systemctl status devops-app` → active, браузер и /health работают.
Если БД запускается позже, приложение должно восстановиться при повторной попытке.

## 9. Повторение с нуля

Этот раздел не заменяет уже выполненную настройку. Для нового стенда:
1. Установите Ubuntu Server 24.04 LTS без GUI на две ВМ (2 CPU, 2 ГБ RAM, диск 20 ГБ).
2. Настройте NAT + VMnet1 Host-only 192.0.2.0/24, статические ens34 .10/.20 без gateway/DNS.
3. Создайте администратора, установите openssh-server, проверьте ключевой вход с Windows.
4. После успешного входа ключом отключите PermitRootLogin, PasswordAuthentication,
   KbdInteractiveAuthentication, оставив PubkeyAuthentication=yes и AllowUsers
   devopsadmin. Перед reload: `sudo /usr/sbin/sshd -t`.
5. На обеих машинах: `sudo systemctl set-default multi-user.target`.
6. На db-server: `sudo apt update`, `sudo apt install -y postgresql-16 postgresql-client-16 ufw`,
   `sudo systemctl enable postgresql`.
7. Скопируйте исходники как в разделе 2. Только на пустом новом окружении:
   `sudo -u postgres psql -X -v ON_ERROR_STOP=1 -f /var/tmp/devops-lr2/deploy/00-create-database.sql`.
   Затем `sudo -u postgres psql`, в psql: `\password devops_app`, `\q`.
8. В postgresql.conf задайте `listen_addresses = '127.0.0.1,192.0.2.20'`.
   В pg_hba.conf добавьте точное основное правило
   `host devops devops_app 192.0.2.10/32 scram-sha-256`, оставив локальные.
9. На db-server включите systemd-networkd-wait-online.service. В
   /etc/systemd/system/postgresql@16-main.service.d/10-network.conf запишите
   [Unit], Wants=network-online.target, After=network-online.target.
   Затем daemon-reload и restart postgresql@16-main.
10. UFW db-server: incoming deny, outgoing allow, разрешить TCP 22 с .77.1
    и TCP 5432 с .77.10, затем enable.
11. Выполните разделы 3–8: схема, тесты, установка, env, firewall, защита.

Не включайте GUI, контейнеры и сторонние способы удаленного администрирования.

## 10. Обновление кода и выпуск

Обновление вручную: скопируйте проверенный код в пользовательский devops-work,
снова запустите install-app.sh, затем `sudo systemctl restart devops-app`.
Настоящий app.env сохраняется. После изменения env тоже нужен restart.
Схема этой ЛР не является механизмом автоматического обновления структуры БД.

GitFlow: feature/lr2-postgresql-linux → PR в develop. После проверки кода и фактического
развертывания: release/0.2.0 от develop, установить версию 0.2.0, повторить проверки,
PR в main и обратное слияние в develop. Тег v0.2.0 ставится на принятый релизный
коммит main; старый v0.1.0 не перемещается. Выпуск не автоматизирован.
