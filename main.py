# Словари
english_words = {
    "город": "city", "вода": "water", "метро": "underground",
    "яблоко": "apple", "семья": "family", "сестра": "sister",
    "чай": "tea", "математика": "maths", "цветок": "flower",
    "дерево": "tree", "река": "river", "торт": "cake",
    "старый": "old", "маленький": "small", "кот": "cat",
    "мясо": "meat", "банк": "bank", "расписка": "note",
    "видео": "video", "книга": "book"
}


# Списки
russia_words = list(english_words)


# Фукции
def record_errors(eng_word, ru_word):
    # Запись английского слово в фаил
    eng_word = eng_word + "\n"
    file = open("word_error.txt", mode="a", encoding="utf-8")
    file.write(eng_word)
    file.close()
    
    
    # Запись русского слово в фаил
    ru_word = ru_word + "\n"
    file = open("translate_errors.txt", mode="a", encoding="utf-8")
    file.write(ru_word)
    file.close()
    
    
def open_errors():
    # открытие английских слов
    with open("word_error.txt", mode="r", encoding="utf-8") as file:
        user_errors = file.readlines()
    
    
    # открытие русских слов
    with open("translate_errors.txt", mode="r", encoding="utf-8") as file:
        translate_errors = file.readlines()
    return user_errors, translate_errors


def practice(russia_words,english_words):
    mark_check = 10
    while True:
        mark = 0
        
        
        for ru_word in russia_words:
            text_input = "Введите перевод этого слова: "
            user_input = input(f"{text_input} {ru_word}\nПеревод сюда: ").strip().lower()

            # Получаем правильный перевод из словаря
            eng_word = english_words[ru_word]
            if user_input == eng_word:
                mark += 1
                print("Вы ввели правильно!")
            else:
                print(f"Вы ввели неправильно. Правильный ответ: {eng_word}")
                # Активация функции
                record_errors(eng_word, ru_word)
                
            
            text_answer = "1-продолжить тренировку\n2-выход\nВвод сюда: "
            if mark == mark_check:
                user_choice = int(input(text_answer))
                if user_choice == 1:
                    mark_check = mark_check + 5
                    print(f"Вы набрали {mark} баллов")
                else:
                    print(f"Вы набрали {mark} баллов")
                    break
        if user_choice == 2:
            break


def error_correction():
    user_errors, translate_errors = open_errors()
    
    
    print("Сейчас вы потренеруете слова в которых допустили ошибку")
    
    mark = 0
    i = 0 
    while i < len(translate_errors):
        user_error = user_errors[i].replace("\n", "")        
        translate_error = translate_errors[i].replace("\n", "")
        text_input = "Введите перевод этого слова:"
        user_answer = input(f"{text_input} {translate_error}\nПеревод сюда: ")
        if user_answer == user_error:
            print("Вы ввели правильно!")
            mark += 1
        else:
            print(f"Вы ввели неправильно. Правильный ответ: {user_errors[i]}")
        i += 1
        print(f"Вы набрали {mark} баллов")


def main_menu(russia_words,english_words):
     while True:
         text_menu = "1 - тренировка\n2 - работа над ошибками\n3 - выйти\nВведите цифру: "
         user_answer = input(text_menu)
        
        
         if user_answer == "1":
            practice(russia_words,english_words)
         elif user_answer == "2":
            error_correction()
         elif user_answer == "3":
             exit("вы вышли из программы")
         else:
             print("неизвестная комманда")


# Приветствие
text_hello = "Добро пожаловать!\nМы будем показывать вам русское слово, а вы будете писать его английский перевод.\nНажмите Enter, чтобы продолжить: "
input(text_hello)


# меню тренажёра
main_menu(russia_words,english_words)