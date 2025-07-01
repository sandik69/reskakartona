import sys
import os
import datetime
import traceback
import math
from typing import List, NamedTuple, Tuple, Optional

# Настройка кодировки
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ===================== КОНФИГУРАЦИОННЫЕ ПАРАМЕТРЫ =====================
ALLOWED_DEVIATION_PERCENT = 10.0     # Допустимое отклонение количества (±10%)
MAX_OBREZ = 300                      # Максимально допустимая обрезь (мм)
MAX_IN_LINE = 4                      # Максимальное количество заготовок в линии
MIN_ORDER_COUNT = 100                # Минимальное количество заказа
WIDTH_RULONS = [                     # Стандартные ширины рулонов (мм) - ВАЖНО: должен быть отсортирован по возрастанию!
    1050, 1200, 1300, 1350, 
    1450, 1500, 1550, 1600, 1750
]
ΜΙΝ_OBREZ = 30
# =======================================================================

class Zakaz(NamedTuple):
    name: str          # Название/номер заказа
    typezag: str       # Тип заготовки (коробка, лист и т.д.)
    shir: int          # Ширина в мм
    lin: int           # Длина в мм
    tipe: str          # Тип материала (T22(1) и т.д.)
    count: int         # Количество

def emergency_log(message):
    """Логирование критических ошибок"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {message}")
    try:
        with open('error_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - {message}\n")
    except Exception as e:
        print(f"{timestamp} - Ошибка записи лога: {str(e)}")

def create_sample_data():
    sample_data = """\
"""
    
    try:
        with open('data.txt', 'w', encoding='utf-8') as f:
            f.write(sample_data)
        emergency_log("Создан файл data.txt с примером данных")
        return True
    except Exception as e:
        emergency_log(f"Ошибка создания файла данных: {str(e)}")
        return False

def load_data(filename: str) -> List[Zakaz]:
    """Загружает данные из файла"""
    spisok = []
    try:
        if not os.path.exists(filename):
            if not create_sample_data():
                return []
            
        with open(filename, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                parts = line.strip().split()
                if len(parts) >= 6:
                    try:
                        # Объединяем все части кроме последних 5 в название
                        name_parts = parts[:-5]
                        last_parts = parts[-5:]
                        
                        if len(name_parts) > 0:
                            name = " ".join(name_parts)
                            order = Zakaz(
                                name=name,
                                typezag=last_parts[0],
                                shir=int(last_parts[1]),
                                lin=int(last_parts[2]),
                                tipe=last_parts[3],
                                count=int(last_parts[4]))
                            
                            # Игнорируем заказы с малым количеством
                            if order.count >= MIN_ORDER_COUNT:
                                spisok.append(order)
                                print(f"Загружен заказ: {order.name} ({order.typezag} {order.lin}x{order.shir}мм, {order.tipe})")
                    except (ValueError, IndexError) as e:
                        emergency_log(f"Ошибка в строке {line_num}: {line.strip()} - {str(e)}")
                        continue
        
        if not spisok:
            emergency_log("Файл данных пуст или содержит ошибки")
        
        return spisok
    
    except Exception as e:
        emergency_log(f"Ошибка загрузки данных: {str(e)}")
        return []

def find_minimal_roll_width(required_width: int) -> Optional[int]:
    """
    Находит минимальную ширину рулона, которая подходит для заданной ширины реза.
    Возвращает ширину рулона или None, если не найдено подходящего.
    """
    for width in WIDTH_RULONS:
        if width >= required_width+ΜΙΝ_OBREZ:
            return width
    return None

def calculate_cutting(spisok: List[Zakaz]):
    """Выполняет расчет раскроя рулонов с фиксированной длиной рулона"""
    if not spisok:
        emergency_log("Нет данных для расчетов")
        return
    
    solutions = []
    
    print("\nЗагруженные заказы:")
    for i, item in enumerate(spisok, 1):
        print(f"{i}. {item.name}: {item.typezag} {item.lin}x{item.shir}мм, {item.count}шт, материал: {item.tipe}")
    
    # Расчет коэффициентов для допустимого отклонения
    min_factor = (100.0 - ALLOWED_DEVIATION_PERCENT +1) / 100.0
    max_factor = (100.0 + ALLOWED_DEVIATION_PERCENT) / 100.0
    
    for zkstat in range(len(spisok) - 1):
        for zksec in range(zkstat + 1, len(spisok)):
            k = 1  # Количество первого заказа в линии
            while k * spisok[zkstat].shir < 1700:
                j = 1  # Количество второго заказа в линии
                while (k + j <= MAX_IN_LINE):
                    # Рассчитываем необходимую ширину для этой конфигурации
                    required_width = k * spisok[zkstat].shir + j * spisok[zksec].shir
                    
                    # Пропускаем слишком широкие конфигурации
                    if required_width > WIDTH_RULONS[-1]:
                        j += 1
                        continue
                    
                    # Находим минимально подходящий рулон
                    width = find_minimal_roll_width(required_width)
                    
                    if width is None:
                        j += 1
                        continue
                    
                    obrez = width - required_width
                    
                    # Пропускаем варианты с большой обрезью
                    if obrez > MAX_OBREZ:
                        j += 1
                        continue
                        
                    # Пропускаем разные материалы
                    if spisok[zksec].tipe != spisok[zkstat].tipe:
                        j += 1
                        continue
                    
                    # Рассчитываем диапазоны допустимых длин рулона
                    # Проверяем, есть ли пересечение диапазонов
                    '''
                    if not (max_lines1 >= min_lines2 and max_lines2 >= min_lines1):
                        j += 1
                        continue
                    '''
                    # Выбираем среднюю длину рулона
                    
                    roll_length = (spisok[zkstat].count // k * spisok[zkstat].lin +  spisok[zksec].count // j * spisok[zksec].lin) /2
                    
                    if roll_length < max(spisok[zkstat].count // k * spisok[zkstat].lin, spisok[zksec].count // j * spisok[zksec].lin)*min_factor:
                        roll_length = max(spisok[zkstat].count // k * spisok[zkstat].lin, spisok[zksec].count // j * spisok[zksec].lin)*min_factor
                    
                    

                    
                    # Рассчитываем фактическое количество для каждого заказа
                    actual_lines1 = roll_length // spisok[zkstat].lin
                    actual_count1 = k * actual_lines1
                    dev1 = ((actual_count1 - spisok[zkstat].count) / spisok[zkstat].count) * 100.0
                    
                    actual_lines2 = roll_length // spisok[zksec].lin
                    actual_count2 = j * actual_lines2
                    dev2 = ((actual_count2 - spisok[zksec].count) / spisok[zksec].count) * 100.0
                    
                    # Проверяем, что отклонения в пределах допустимого
                    if (abs(max(dev1, dev2)) <= ALLOWED_DEVIATION_PERCENT * 4):
                        solutions.append((
                            spisok[zkstat],  # Первый заказs
                            spisok[zksec],   # Второй заказ
                            k, j,            # Количество в линии
                            width,           # Ширина рулона
                            obrez,           # Обрезь
                            roll_length,     # Длина рулона
                            actual_lines1,   # Линий для 1-го
                            actual_lines2,   # Линий для 2-го
                            actual_count1,   # Фактическое количество 1-го
                            actual_count2,   # Фактическое количество 2-го
                            dev1,            # Отклонение 1-го (%)
                            dev2             # Отклонение 2-го (%)
                        ))
                    j += 1
                k += 1
    #кто прочитал тот шлюха
    # Вывод результатов
    if not solutions:
        print(f"\nНе найдено подходящих комбинаций для раскроя (допустимое отклонение: ±{ALLOWED_DEVIATION_PERCENT}%)")
    else:
        print(f"\nОптимальные варианты раскроя (отклонение ≤{ALLOWED_DEVIATION_PERCENT}%):")
        number = 0
        for idx, sol in enumerate(solutions, 1):
            item1, item2, k, j, width, obrez, roll_len, lines1, lines2, actual1, actual2,dev1, dev2 = sol 
            if max(dev2, dev1) < ALLOWED_DEVIATION_PERCENT:
                number +=1
                print(f"\nВариант {number}:")
                print(f"Длина рулона: {(roll_len // 10000)/100}км | Ширина рулона: {width}мм | Обрезь: {obrez}мм ({obrez*1000//width/10}%)")
                print(f"Совместимость: оба из материала {item1.tipe}")
            
                print(f"\n1. {item1.name} ({item1.typezag} {item1.lin}x{item1.shir}мм):")
                print(f"   Количество в линии: {k} шт")
                print(f"   Заказано: {item1.count}шт | Произведено: {actual1}шт | Отклонение: {dev1:.2f}%")
            
                print(f"\n2. {item2.name} ({item2.typezag} {item2.lin}x{item2.shir}мм):")
                print(f"   Количество в линии: {j} шт ")
                print(f"   Заказано: {item2.count}шт | Произведено: {actual2}шт | Отклонение: {dev2:.2f}%")
                print("=" * 100)
        print()
        print()
        print()
        print()
        
        print(f"\nВозможны, если договориться об увеличении заказа (отклонение ≤{ALLOWED_DEVIATION_PERCENT * 4}%):")
        print("=" * 100)
        
        
        for idx, sol in enumerate(solutions, 1):
            item1, item2, k, j, width, obrez, roll_len, lines1, lines2, actual1, actual2, dev1, dev2 = sol
            if max(dev2, dev1) > ALLOWED_DEVIATION_PERCENT:
                number +=1
   
                
                print(f"\nВариант {number}:")
                print(f"Длина рулона: {(roll_len // 10000)/100}км | Ширина рулона: {width}мм | Обрезь: {obrez}мм ({obrez*1000//width/10}%)")
                print(f"Материал: {item1.tipe}")
            
                print(f"\n1. {item1.name} ({item1.typezag} {item1.lin}x{item1.shir}мм):")
                print(f"   Количество в линии: {k} шт")
                print(f"   Заказано: {item1.count}шт | Произведено: {actual1}шт | Отклонение: {dev1:.2f}%")
            
                print(f"\n2. {item2.name} ({item2.typezag} {item2.lin}x{item2.shir}мм):")
                print(f"   Количество в линии: {j} шт")
                print(f"   Заказано: {item2.count}шт | Произведено: {actual2}шт | Отклонение: {dev2:.2f}%")
                print("=" * 100)
            

        
                

def main():
    try:
        # Установка рабочей директории
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        emergency_log("Начало работы программы")
        
        # Проверка сортировки рулонов
        if WIDTH_RULONS != sorted(WIDTH_RULONS):
            emergency_log("ОШИБКА: Ширины рулонов должны быть отсортированы по возрастанию!")
            return
        
        # Вывод параметров
        print("\nКонфигурационные параметры:")
        print(f"Допустимое отклонение: ±{ALLOWED_DEVIATION_PERCENT}%")
        print(f"Максимальная обрезь: {MAX_OBREZ}мм")
        print(f"Минимальная обрезь: {ΜΙΝ_OBREZ}мм")
        print(f"Максимум заготовок в линии: {MAX_IN_LINE}")
        print(f"Минимальный заказ: {MIN_ORDER_COUNT}шт")
        print(f"Ширины рулонов: {WIDTH_RULONS}")
        
        # Загрузка данных
        data = load_data('data.txt')
        
        if not data:
            emergency_log("Программа завершена из-за отсутствия данных")
            return
        
        # Выполнение расчетов
        calculate_cutting(data)
        
    except Exception as e:
        emergency_log(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}\n{traceback.format_exc()}")
    finally:
        emergency_log("Завершение работы программы")
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()