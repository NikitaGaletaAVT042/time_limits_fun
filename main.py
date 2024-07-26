import os
import time
import schedule
import psutil
import webbrowser
from pymongo import MongoClient
from datetime import datetime
from tkinter import Tk, Entry, Button, Label, Listbox, END, Toplevel, Text, Scrollbar, VERTICAL, RIGHT, Y, Frame
from transformers import BertTokenizer, BertForSequenceClassification
from transformers import pipeline

# Настройки MongoDB
client = MongoClient('localhost', 27017)
db = client['time_tracker']
collection = db['site_usage']

# Список сайтов для блокировки
blocked_sites = [
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "twitch.com",
    "vk.com"
]

# Список разрешенных образовательных видео/каналов YouTube
whitelist_youtube = []

# Время в секундах для разрешенного использования развлекательного контента
allowed_time = 10800  # 3 часа

# Файл hosts для блокировки сайтов
hosts_path = "C:\\Windows\\System32\\drivers\\etc\\hosts"  # Путь для Windows
redirect_ip = "127.0.0.1"

# Загрузка модели BERT
model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name)
classifier = pipeline('sentiment-analysis', model=model, tokenizer=tokenizer)

def classify_text(text):
    result = classifier(text)
    # Предполагаем, что позитивные оценки связаны с образовательным контентом
    return 1 if result[0]['label'] == '5 stars' else 0

def block_sites():
    with open(hosts_path, 'r+') as file:
        content = file.read()
        for site in blocked_sites:
            if site not in content:
                file.write(f"{redirect_ip} {site}\n")

def unblock_sites():
    with open(hosts_path, 'r+') as file:
        lines = file.readlines()
        file.seek(0)
        for line in lines:
            if not any(site in line for site in blocked_sites):
                file.write(line)
        file.truncate()

def log_site_usage(site, duration):
    collection.insert_one({
        'site': site,
        'duration': duration,
        'timestamp': datetime.now()
    })

def monitor_usage():
    start_time = time.time()
    usage_data = {site: 0 for site in blocked_sites}

    while time.time() - start_time < allowed_time:
        time.sleep(5)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline']:
                for site in blocked_sites:
                    if any(site in cmd for cmd in proc.info['cmdline']):
                        usage_data[site] += 5

    for site, duration in usage_data.items():
        log_site_usage(site, duration)

    print("Лимит времени на развлекательный контент исчерпан. Блокировка сайтов...")
    block_sites()

def add_educational_link():
    url = url_entry.get()
    if url:
        if classify_text(url) == 1:  # Проверяем, является ли контент образовательным
            whitelist_youtube.append(url)
            listbox.insert(END, url)
            url_entry.delete(0, END)
        else:
            print("Добавленная ссылка не является образовательной.")

def open_url(url):
    if any(url.startswith(edu_url) for edu_url in whitelist_youtube):
        webbrowser.open(url)
    else:
        print("Доступ к развлекательному контенту ограничен.")

def show_add_link_window():
    add_link_window = Toplevel(root)
    add_link_window.title("Добавить образовательную ссылку YouTube")

    label = Label(add_link_window, text="Добавить образовательную ссылку YouTube:")
    label.pack()

    global url_entry
    url_entry = Entry(add_link_window, width=50)
    url_entry.pack()

    add_button = Button(add_link_window, text="Добавить", command=add_educational_link)
    add_button.pack()

    global listbox
    listbox = Listbox(add_link_window, width=80, height=10)
    listbox.pack()

    for url in whitelist_youtube:
        listbox.insert(END, url)

def show_statistics_window():
    stats_window = Toplevel(root)
    stats_window.title("Статистика использования сайтов")

    stats_frame = Frame(stats_window)
    stats_frame.pack(fill="both", expand=True)

    scrollbar = Scrollbar(stats_frame, orient=VERTICAL)
    scrollbar.pack(side=RIGHT, fill=Y)

    stats_text = Text(stats_frame, wrap="word", yscrollcommand=scrollbar.set)
    stats_text.pack(fill="both", expand=True)

    scrollbar.config(command=stats_text.yview)

    stats_text.insert(END, "Сайт\t\tВремя (сек)\t\tДата\n")
    stats_text.insert(END, "-"*50 + "\n")

    for record in collection.find():
        stats_text.insert(END, f"{record['site']}\t\t{record['duration']}\t\t{record['timestamp']}\n")

def main():
    unblock_sites()
    schedule.every().day.at("08:00").do(unblock_sites)  # Разблокировка сайтов в 8 утра
    schedule.every().day.at("08:01").do(monitor_usage)  # Начало мониторинга в 8:01

    global root
    root = Tk()
    root.title("Контроль контента")

    add_link_button = Button(root, text="Добавить образовательные ссылки", command=show_add_link_window)
    add_link_button.pack()

    stats_button = Button(root, text="Показать статистику", command=show_statistics_window)
    stats_button.pack()

    root.mainloop()

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
