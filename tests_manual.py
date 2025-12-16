import os
import sys
import builtins
import io
import importlib.util


APP = None


def _remove_all_in_dir(path):
    if not os.path.isdir(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def _mock_inputs(answers):
    original_input = builtins.input
    index = 0

    def fake_input(_prompt=""):
        nonlocal index
        if index >= len(answers):
            raise AssertionError("Тест запросил input() больше раз, чем ожидалось")
        value = answers[index]
        index += 1
        return value

    builtins.input = fake_input

    def restore():
        builtins.input = original_input

    return restore


def _capture_stdout(func):
    original_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        func()
    finally:
        sys.stdout = original_stdout
    return buf.getvalue()


def _remove_error_files():
    for path in ("word_error.txt", "translate_errors.txt"):
        if os.path.exists(path):
            os.remove(path)


def _mock_exit():
    original_exit = getattr(builtins, "exit", None)

    def fake_exit(message=None):
        raise SystemExit(message)

    builtins.exit = fake_exit

    def restore():
        if original_exit is None:
            delattr(builtins, "exit")
        else:
            builtins.exit = original_exit

    return restore


def _count_substring(text, sub):
    count = 0
    start = 0
    while True:
        idx = text.find(sub, start)
        if idx == -1:
            return count
        count += 1
        start = idx + len(sub)


def _load_main_module_without_running(repo_root, fail_on_input=True):
    original_input = builtins.input

    def fail_input(_prompt=""):
        raise AssertionError("input() не должен вызываться при импорте модуля")

    if fail_on_input:
        builtins.input = fail_input

    try:
        path = os.path.join(repo_root, "main.py")
        spec = importlib.util.spec_from_file_location("main_isolated_for_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        builtins.input = original_input


def test_read_lines_missing_file():
    """Проверяем: если файла нет, read_lines возвращает [], чтобы программа не падала."""
    missing = "no_such_file_hopefully.txt"
    if os.path.exists(missing):
        os.remove(missing)
    lines = APP.read_lines(missing)
    assert lines == [], "Ожидали пустой список для отсутствующего файла"


def test_read_lines_existing_file():
    """Проверяем: если файл есть, read_lines возвращает строки ровно как в файле (включая \\n)."""
    path = "sample_lines.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("a\nb\n")
    lines = APP.read_lines(path)
    assert lines == ["a\n", "b\n"], "read_lines должен возвращать результат readlines() без изменений"


def test_read_lines_empty_file():
    """Проверяем: пустой файл даёт пустой список, чтобы не было лишних 'пустых' элементов."""
    path = "empty.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("")
    lines = APP.read_lines(path)
    assert lines == [], "Для пустого файла ожидается []"


def test_normalize_lines_in_place():
    """Проверяем: normalize_lines удаляет \\n и меняет список in-place, чтобы дальше работала проверка дубликатов."""
    lines = ["a\n", "b", "c\n"]
    before_id = id(lines)
    APP.normalize_lines(lines)
    assert id(lines) == before_id, "Список должен меняться in-place, а не заменяться новым"
    assert lines == ["a", "b", "c"], "Должны удаляться только символы переноса строки"


def test_record_errors_first_write_creates_files():
    """Проверяем: record_errors при первой записи создаёт/дописывает оба файла, чтобы ошибки сохранялись."""
    _remove_error_files()
    APP.record_errors("city", "город")
    assert os.path.exists("word_error.txt"), "Должен создаваться файл word_error.txt"
    assert os.path.exists("translate_errors.txt"), "Должен создаваться файл translate_errors.txt"
    assert APP.read_lines("word_error.txt") == ["city\n"], "В word_error.txt должна появиться строка с английским словом"
    assert APP.read_lines("translate_errors.txt") == ["город\n"], "В translate_errors.txt должна появиться строка с русским словом"


def test_record_errors_no_duplicates_on_repeat():
    """Проверяем: повторная запись того же eng_word не создаёт дубликаты, чтобы ошибки не разрастались."""
    _remove_error_files()
    APP.record_errors("city", "город")
    APP.record_errors("city", "город")
    assert APP.read_lines("word_error.txt") == ["city\n"], "Не должно быть дублей в word_error.txt"
    assert APP.read_lines("translate_errors.txt") == ["город\n"], "Не должно быть дублей в translate_errors.txt"


def test_record_errors_existing_newline_is_detected():
    """Проверяем: если в файле строки с \\n, normalize_lines влияет на сравнение и дубликаты не пишутся."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\n")
    APP.record_errors("city", "ГОРОД-ДРУГОЙ")
    assert APP.read_lines("word_error.txt") == ["city\n"], "Строка не должна дублироваться из-за наличия \\n"
    assert APP.read_lines("translate_errors.txt") == ["город\n"], "При наличии дубликата eng_word не должно дописываться и русское слово"


def test_record_errors_appends_second_word():
    """Проверяем: разные ошибки дописываются в конец файлов, чтобы сохранялся порядок появления ошибок."""
    _remove_error_files()
    APP.record_errors("city", "город")
    APP.record_errors("water", "вода")
    assert APP.read_lines("word_error.txt") == ["city\n", "water\n"], "Ожидали две строки в word_error.txt в порядке записи"
    assert APP.read_lines("translate_errors.txt") == ["город\n", "вода\n"], "Ожидали две строки в translate_errors.txt в порядке записи"


def test_error_correction_no_files_does_not_call_input():
    """Проверяем: когда файлов ошибок нет, error_correction отрабатывает пусто и не вызывает input()."""
    _remove_error_files()

    original_input = builtins.input

    def fail_input(_prompt=""):
        raise AssertionError("input() не должен вызываться, если ошибок нет")

    builtins.input = fail_input
    try:
        APP.error_correction()
    finally:
        builtins.input = original_input


def test_error_correction_one_correct_answer_prints_success():
    """Проверяем: при одной ошибке и правильном ответе печатается 'Вы ввели правильно!', чтобы была обратная связь."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\n")

    restore = _mock_inputs(["city"])
    try:
        out = _capture_stdout(APP.error_correction)
    finally:
        restore()

    assert "Вы ввели правильно!" in out, "Ожидали сообщение о правильном вводе"
    assert "Вы набрали 1 баллов" in out, "Ожидали, что счёт увеличится до 1"


def test_error_correction_one_wrong_answer_prints_correct():
    """Проверяем: при неправильном ответе печатается правильный ответ, чтобы пользователь понимал ошибку."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\n")

    restore = _mock_inputs(["wrong"])
    try:
        out = _capture_stdout(APP.error_correction)
    finally:
        restore()

    assert "Вы ввели неправильно." in out, "Ожидали сообщение о неправильном вводе"
    assert "Правильный ответ:" in out, "Ожидали вывод правильного ответа"


def test_error_correction_mismatched_lengths_no_index_error():
    """Проверяем: если количество строк в двух файлах разное, error_correction не падает с IndexError."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\nрека\n")

    restore = _mock_inputs(["city"])
    try:
        _capture_stdout(APP.error_correction)
    finally:
        restore()


def test_error_correction_user_errors_longer_than_translates():
    """Проверяем: если word_error.txt длиннее translate_errors.txt, берётся минимальная длина и input вызывается 1 раз."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\nwater\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\n")

    restore = _mock_inputs(["city"])
    try:
        out = _capture_stdout(APP.error_correction)
    finally:
        restore()

    assert "Вы набрали" in out, "Ожидали корректное завершение без ошибок"


def test_import_main_has_no_interactive_side_effects():
    """Проверяем: импорт main.py не вызывает input() и не запускает меню, чтобы тесты могли импортировать модуль."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    module = _load_main_module_without_running(repo_root, fail_on_input=True)
    assert hasattr(module, "read_lines"), "Ожидали, что функции доступны после импорта"


def test_practice_all_correct_exits_and_no_error_files():
    """Проверяем: practice завершается при 10 правильных ответах и выборе выхода, чтобы не было зависаний."""
    _remove_error_files()

    ru_words = [
        "город", "вода", "метро", "яблоко", "семья",
        "сестра", "чай", "математика", "цветок", "дерево",
    ]
    eng_map = {
        "город": "city",
        "вода": "water",
        "метро": "underground",
        "яблоко": "apple",
        "семья": "family",
        "сестра": "sister",
        "чай": "tea",
        "математика": "maths",
        "цветок": "flower",
        "дерево": "tree",
    }

    answers = []
    i = 0
    while i < len(ru_words):
        answers.append("  " + eng_map[ru_words[i]].upper() + "  ")
        i += 1
    answers.append("2")

    restore = _mock_inputs(answers)
    try:
        out = _capture_stdout(lambda: APP.practice(ru_words, eng_map))
    finally:
        restore()

    assert _count_substring(out, "Вы ввели правильно!") == 10, "Ожидали 10 сообщений о правильном вводе"
    assert not os.path.exists("word_error.txt"), "При всех правильных ответах ошибки не должны записываться"
    assert not os.path.exists("translate_errors.txt"), "При всех правильных ответах ошибки не должны записываться"


def test_main_menu_smoke_training_then_exit():
    """Проверяем: main_menu проходит сценарий 'тренировка' -> 'выход' без зависаний и падений."""
    _remove_error_files()

    ru_words = [
        "город", "вода", "метро", "яблоко", "семья",
        "сестра", "чай", "математика", "цветок", "дерево",
    ]
    eng_map = {
        "город": "city",
        "вода": "water",
        "метро": "underground",
        "яблоко": "apple",
        "семья": "family",
        "сестра": "sister",
        "чай": "tea",
        "математика": "maths",
        "цветок": "flower",
        "дерево": "tree",
    }

    answers = ["1"]
    i = 0
    while i < len(ru_words):
        answers.append(eng_map[ru_words[i]])
        i += 1
    answers.append("2")
    answers.append("3")

    restore_input = _mock_inputs(answers)
    restore_exit = _mock_exit()
    try:
        try:
            _capture_stdout(lambda: APP.main_menu(ru_words, eng_map))
            assert False, "Ожидали SystemExit при выборе пункта 3"
        except SystemExit as e:
            assert e.code is not None, "Ожидали сообщение выхода из программы"
    finally:
        restore_exit()
        restore_input()


def test_known_issue_error_correction_should_accept_trim_and_case_insensitive():
    """Проверяем (недоработка): правильный ответ с пробелами/регистром должен засчитываться, чтобы UX был дружелюбнее."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\n")

    restore = _mock_inputs(["  CITY  "])
    try:
        out = _capture_stdout(APP.error_correction)
    finally:
        restore()

    assert "Вы ввели правильно!" in out, "Ожидали, что ввод будет нормализован (strip/lower) и ответ засчитается"


test_known_issue_error_correction_should_accept_trim_and_case_insensitive.expected_failure = True


def test_known_issue_practice_can_exit_even_with_mistake():
    """Проверяем (недоработка): после ошибок должен быть способ выйти из practice, чтобы тренировка не зацикливалась."""
    _remove_error_files()

    ru_words = [
        "город", "вода", "метро", "яблоко", "семья",
        "сестра", "чай", "математика", "цветок", "дерево",
    ]
    eng_map = {
        "город": "city",
        "вода": "water",
        "метро": "underground",
        "яблоко": "apple",
        "семья": "family",
        "сестра": "sister",
        "чай": "tea",
        "математика": "maths",
        "цветок": "flower",
        "дерево": "tree",
    }

    answers = []
    i = 0
    while i < len(ru_words):
        if i == 0:
            answers.append("wrong")  # специально делаем 1 ошибку
        else:
            answers.append(eng_map[ru_words[i]])
        i += 1
    answers.append("2")  # ожидаем, что нас спросят "продолжить/выход" и мы выберем выход

    restore = _mock_inputs(answers)
    try:
        _capture_stdout(lambda: APP.practice(ru_words, eng_map))
    finally:
        restore()


test_known_issue_practice_can_exit_even_with_mistake.expected_failure = True


def test_known_issue_practice_choice_should_not_crash_on_non_int():
    """Проверяем (недоработка): выбор 'продолжить/выход' не должен падать на нечисловом вводе."""
    _remove_error_files()

    ru_words = [
        "город", "вода", "метро", "яблоко", "семья",
        "сестра", "чай", "математика", "цветок", "дерево",
    ]
    eng_map = {
        "город": "city",
        "вода": "water",
        "метро": "underground",
        "яблоко": "apple",
        "семья": "family",
        "сестра": "sister",
        "чай": "tea",
        "математика": "maths",
        "цветок": "flower",
        "дерево": "tree",
    }

    answers = []
    i = 0
    while i < len(ru_words):
        answers.append(eng_map[ru_words[i]])
        i += 1
    answers.append("abc")  # сейчас это приводит к ValueError в int(...)

    restore = _mock_inputs(answers)
    try:
        _capture_stdout(lambda: APP.practice(ru_words, eng_map))
    finally:
        restore()


test_known_issue_practice_choice_should_not_crash_on_non_int.expected_failure = True


def test_main_menu_unknown_command_then_exit():
    """Проверяем: main_menu не падает на неизвестных командах и позволяет потом выйти."""
    _remove_error_files()
    restore_input = _mock_inputs(["0", "abc", "3"])
    restore_exit = _mock_exit()
    try:
        def run_menu():
            try:
                APP.main_menu([], {})
            except SystemExit:
                return

        out = _capture_stdout(run_menu)
    finally:
        restore_exit()
        restore_input()

    assert _count_substring(out, "неизвестная комманда") == 2, "Ожидали сообщение об ошибке для двух неверных вводов"


def test_run_smoke_exit():
    """Проверяем: run() можно завершить без ручного ввода (Enter + '3'), чтобы запуск был тестируемым."""
    restore_input = _mock_inputs(["", "3"])
    restore_exit = _mock_exit()
    try:
        try:
            _capture_stdout(APP.run)
            assert False, "Ожидали SystemExit при выборе пункта 3"
        except SystemExit:
            pass
    finally:
        restore_exit()
        restore_input()


def test_known_issue_read_lines_non_utf8_should_not_crash():
    """Проверяем (недоработка): read_lines не должен падать на файле с не-UTF8, чтобы быть устойчивее."""
    path = "bad_encoding.txt"
    with open(path, "wb") as f:
        f.write(b"\xff\xfe\xfa")
    lines = APP.read_lines(path)
    assert lines == [], "Ожидали, что не-UTF8 файл будет обработан безопасно (например, вернуть [])"


test_known_issue_read_lines_non_utf8_should_not_crash.expected_failure = True


def test_known_issue_normalize_lines_should_remove_carriage_return():
    """Проверяем (недоработка): normalize_lines должен убирать '\\r' из Windows-строк, чтобы сравнение работало одинаково."""
    lines = ["a\r\n", "b\r\n"]
    APP.normalize_lines(lines)
    assert lines == ["a", "b"], "Ожидали удаление и \\n, и \\r"


test_known_issue_normalize_lines_should_remove_carriage_return.expected_failure = True


def test_known_issue_record_errors_case_insensitive_no_duplicates():
    """Проверяем (недоработка): record_errors не должен плодить дубликаты при разном регистре (City/city)."""
    _remove_error_files()
    APP.record_errors("City", "город")
    APP.record_errors("city", "город")
    eng_lines = APP.read_lines("word_error.txt")
    assert len(eng_lines) == 1, "Ожидали отсутствие дублей при отличии только регистром"


test_known_issue_record_errors_case_insensitive_no_duplicates.expected_failure = True


def test_known_issue_record_errors_should_ignore_empty_inputs():
    """Проверяем (недоработка): пустые/пробельные слова не должны записываться в ошибки."""
    _remove_error_files()
    APP.record_errors("", "   ")
    assert not os.path.exists("word_error.txt"), "Ожидали, что пустые данные не создают файл ошибок"
    assert not os.path.exists("translate_errors.txt"), "Ожидали, что пустые данные не создают файл ошибок"


test_known_issue_record_errors_should_ignore_empty_inputs.expected_failure = True


def test_known_issue_record_errors_should_keep_pairs_in_sync():
    """Проверяем (недоработка): если английское слово уже есть, но перевода нет, пара должна синхронизироваться."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    # translate_errors.txt намеренно не создаём/не заполняем
    APP.record_errors("city", "город")
    ru_lines = APP.read_lines("translate_errors.txt")
    assert ru_lines == ["город\n"], "Ожидали восстановления пары (дописать перевод для уже существующего слова)"


test_known_issue_record_errors_should_keep_pairs_in_sync.expected_failure = True


def test_known_issue_error_correction_should_clear_fixed_errors():
    """Проверяем (недоработка): после правильного исправления ошибка должна удаляться из файлов."""
    _remove_error_files()
    with open("word_error.txt", "w", encoding="utf-8") as f:
        f.write("city\n")
    with open("translate_errors.txt", "w", encoding="utf-8") as f:
        f.write("город\n")

    restore = _mock_inputs(["city"])
    try:
        _capture_stdout(APP.error_correction)
    finally:
        restore()

    assert APP.read_lines("word_error.txt") == [], "Ожидали очистку исправленной ошибки"
    assert APP.read_lines("translate_errors.txt") == [], "Ожидали очистку исправленной ошибки"


test_known_issue_error_correction_should_clear_fixed_errors.expected_failure = True


def test_known_issue_practice_writes_error_files_before_hang():
    """Проверяем (недоработка): даже если practice зацикливается при ошибке, ошибка должна успеть записаться в файлы."""
    _remove_error_files()

    ru_words = [
        "город", "вода", "метро", "яблоко", "семья",
        "сестра", "чай", "математика", "цветок", "дерево",
    ]
    eng_map = {
        "город": "city",
        "вода": "water",
        "метро": "underground",
        "яблоко": "apple",
        "семья": "family",
        "сестра": "sister",
        "чай": "tea",
        "математика": "maths",
        "цветок": "flower",
        "дерево": "tree",
    }

    answers = []
    i = 0
    while i < len(ru_words):
        if i == 0:
            answers.append("wrong")
        else:
            answers.append(eng_map[ru_words[i]])
        i += 1

    restore = _mock_inputs(answers)
    try:
        try:
            _capture_stdout(lambda: APP.practice(ru_words, eng_map))
        except AssertionError:
            assert os.path.exists("word_error.txt"), "Ожидали, что word_error.txt успеет создаться"
            assert os.path.exists("translate_errors.txt"), "Ожидали, что translate_errors.txt успеет создаться"
            raise AssertionError("practice не должен зацикливаться при наличии ошибок (нет сценария выхода)")
        assert False, "Ожидали, что тест выявит зацикливание/запрос лишних input()"
    finally:
        restore()


test_known_issue_practice_writes_error_files_before_hang.expected_failure = True


def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    test_tmp = os.path.join(repo_root, ".test_tmp")

    os.makedirs(test_tmp, exist_ok=True)
    _remove_all_in_dir(test_tmp)

    old_cwd = os.getcwd()
    try:
        os.chdir(test_tmp)
        sys.path.insert(0, repo_root)

        global APP
        import main as APP_module

        APP = APP_module

        tests = []
        for name, value in sorted(globals().items()):
            if name.startswith("test_") and callable(value):
                tests.append(value)

        passed = 0
        failed = 0
        xfailed = 0
        xpassed = 0

        for test_func in tests:
            is_expected_failure = getattr(test_func, "expected_failure", False)
            try:
                test_func()
                if is_expected_failure:
                    print(f"XPASS: {test_func.__name__} (ожидали падение, но тест прошёл)")
                    xpassed += 1
                else:
                    print(f"PASS: {test_func.__name__}")
                    passed += 1
            except AssertionError as e:
                if is_expected_failure:
                    print(f"XFAIL: {test_func.__name__}: {e}")
                    xfailed += 1
                else:
                    print(f"FAIL: {test_func.__name__}: {e}")
                    failed += 1
            except Exception as e:
                if is_expected_failure:
                    print(f"XFAIL: {test_func.__name__}: {type(e).__name__}: {e}")
                    xfailed += 1
                else:
                    print(f"ERROR: {test_func.__name__}: {type(e).__name__}: {e}")
                    failed += 1

        print(f"\nИтого: passed={passed} failed={failed} xfailed={xfailed} xpassed={xpassed}")
        if failed:
            sys.exit(1)
    finally:
        try:
            os.chdir(old_cwd)
        finally:
            _remove_all_in_dir(test_tmp)


if __name__ == "__main__":
    main()
