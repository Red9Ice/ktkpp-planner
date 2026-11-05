# Инструкция по развертыванию (Deployment Guide)

Данное руководство описывает пошаговый процесс бесплатного облачного развертывания системы автоматизации расписания колледжа согласно ТЗ.

---

## 1. Слой данных: Бесплатный PostgreSQL (Supabase или Neon.tech)

### Вариант А: Supabase (Рекомендуется)
1. Зарегистрируйтесь на [supabase.com](https://supabase.com/).
2. Создайте новый проект (например, `college-timetable`).
3. Перейдите в раздел **SQL Editor**.
4. Скопируйте содержимое файла `data/migrations/001_initial_schema.sql` и выполните запрос (кнопка **Run**).
5. Перейдите в **Project Settings -> Database** и скопируйте строку подключения `Connection String` (URI).
   - Пример: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

### Вариант Б: Neon.tech
1. Зарегистрируйтесь на [neon.tech](https://neon.tech/).
2. Создайте проект и базу данных.
3. В **SQL Editor** выполните скрипт `data/migrations/001_initial_schema.sql`.
4. Скопируйте готовую строку подключения `DATABASE_URL`.

---

## 2. Слой интерфейсов: Бесплатный PaaS для ботов (Render.com)

Боты работают круглосуточно 24/7 в режиме Webhooks, не потребляя ресурсов в моменты простоя.

1. Зарегистрируйтесь на [render.com](https://render.com/).
2. Нажмите **New +** -> **Web Service**.
3. Подключите ваш GitHub репозиторий проекта.
4. Настройте параметры сервиса:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.bot.server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. В разделе **Environment Variables** добавьте:
   - `DATABASE_URL`: строка подключения к Supabase/Neon.
   - `TELEGRAM_BOT_TOKEN`: токен вашего бота от `@BotFather`.
   - `WEBHOOK_URL`: публичный URL вашего Render сервиса (например, `https://college-timetable-bot.onrender.com`).
   - `WEBHOOK_SECRET`: произвольная секретная строка для проверки подлинности вебхука.
   - `GITHUB_TOKEN`: персональный токен GitHub (PAT с правами `repo` и `workflow`) для запуска расчётов.
   - `GITHUB_REPO`: `ваш_логин/репозиторий`.
6. Нажмите **Deploy Web Service**. Render автоматически развернет сервис и зарегистрирует вебхук в Telegram.

---

## 3. Слой ядра: Запуск Solver'а через GitHub Actions

Solver не требует постоянного сервера. Он запускается по требованию:

1. В репозитории GitHub перейдите в **Settings -> Secrets and variables -> Actions**.
2. Добавьте Secret:
   - `DATABASE_URL`: строка подключения к PostgreSQL.
3. Для запуска расчета расписания диспетчер может:
   - **Через Telegram:** отправить боту команду `/generate` (доступно администраторам).
   - **Через GitHub Web:** перейти во вкладку **Actions -> Run College Timetable Solver -> Run workflow**, выбрать режим (`full`, `repair`, `incremental`) и нажать зеленую кнопку.
4. По завершении работы Solver:
   - Результаты автоматически сохраняются в базу данных (таблица `schedule_entries`).
   - Готовый файл `College_Timetable.xlsx` прикрепляется к запуску Action в виде скачиваемого артефакта.
   - Студенты и преподаватели мгновенно видят обновленное расписание в ботах.
