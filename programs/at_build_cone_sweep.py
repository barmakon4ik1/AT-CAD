import math
import matplotlib.pyplot as plt
import numpy as np
from typing import Tuple, List


def build_cone_sweep(D: float, H: float, alpha: float, N: int = 12) -> Tuple[float, List[float], float, float]:
    """
    Рассчитывает параметры и строит развёртку наклонного конуса методом триангуляции как пирамиды с N гранями.
    Нормализует длину дуги основания до 2*pi*R.

    Args:
        D (float): Диаметр основания конуса.
        H (float): Высота конуса.
        alpha (float): Угол наклона оси конуса от вертикали (в градусах).
        N (int): Количество граней пирамиды (должно быть чётным).

    Returns:
        Tuple[float, List[float], float, float]: Угол сектора (в радианах), длины образующих,
                                               минимальная и максимальная длины образующих.

    Raises:
        ValueError: Если входные параметры некорректны.
    """
    if not isinstance(D, (int, float)) or D <= 0:
        raise ValueError(f"Диаметр должен быть положительным числом, получено: {D}")
    if not isinstance(H, (int, float)) or H <= 0:
        raise ValueError(f"Высота должна быть положительным числом, получено: {H}")
    if not isinstance(alpha, (int, float)) or alpha < 0 or alpha >= 90:
        raise ValueError(f"Угол наклона должен быть в диапазоне [0, 90) градусов, получено: {alpha}")
    if N % 2 != 0:
        raise ValueError(f"Количество граней должно быть чётным, получено: {N}")

    # Параметры
    R = D / 2
    alpha_rad = math.radians(alpha)

    # Углы на полной окружности (phi in [0, 2pi])
    phi_vals = np.linspace(0, 2 * math.pi, N, endpoint=False)

    # Вычисление длины образующей
    def get_generatrix_length(phi: float) -> float:
        """Длина образующей для угла phi (в радианах)."""
        return math.sqrt(R ** 2 * (1 + math.sin(alpha_rad) ** 2 - 2 * math.cos(phi) * math.sin(alpha_rad)) + H ** 2)

    # Длины образующих
    generatrix_lengths = [get_generatrix_length(phi) for phi in phi_vals]
    L_min = min(generatrix_lengths)
    L_max = max(generatrix_lengths)

    if L_min <= 0:
        raise ValueError("Конус с такими параметрами невозможен (отрицательная образующая)")

    # Развёртка с линейным распределением
    points = [(0, 0)]  # Вершина конуса на развёртке
    theta_vals = np.linspace(0, 2 * math.pi, N, endpoint=False)  # Равномерное распределение углов

    for i in range(N):
        L_i = generatrix_lengths[i]
        theta_i = theta_vals[i]
        x = L_i * math.cos(theta_i)
        y = L_i * math.sin(theta_i)
        points.append((x, y))

    points.append(points[1])  # Замыкаем контур

    # Нормализация длины дуги
    arc_length_total = 0
    for i in range(N):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        arc_length_total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    scale_factor = (2 * math.pi * R) / arc_length_total if arc_length_total > 0 else 1.0
    points_normalized = [(0, 0)]
    for x, y in points[1:]:
        points_normalized.append((x * scale_factor, y * scale_factor))

    points = points_normalized
    points.append(points[1])  # Замыкаем нормализованный контур

    theta_total = 2 * math.pi  # Полный угол сектора для 2*pi*R

    # Проверка замыкания
    x_last, y_last = points[-1]
    x_first, y_first = points[1]
    distance = math.sqrt((x_last - x_first) ** 2 + (y_last - y_first) ** 2)
    if distance > 1e-3:
        print(f"Предупреждение: контур не замкнут, расстояние между P_0 и P_{N - 1}: {distance:.6f}")

    # Проверка длины дуги основания
    arc_length_total = 0
    for i in range(N):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        arc_length_total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    expected_arc_length_total = 2 * math.pi * R
    print(f"Длина дуги основания на развёртке: {arc_length_total:.2f} (ожидается {expected_arc_length_total:.2f})")

    # Построение развёртки
    fig, ax = plt.subplots()

    # Разделяем x и y координаты точек
    x_points, y_points = zip(*points[1:])  # Пропускаем вершину
    x_points = list(x_points)  # Замыкаем дугу
    y_points = list(y_points)

    # Построение дуги основания (полигон)
    ax.plot(x_points, y_points, 'b-', label='Дуга основания (полигон)')

    # Построение образующих
    for i, (x, y) in enumerate(points[1:], 1):
        ax.plot([0, x], [0, y], 'k-', alpha=0.3)  # Образующие от вершины
        if i == 1:
            ax.plot([0, x], [0, y], 'r-', label=f'L_min={generatrix_lengths[0]:.2f}')
        if i == np.argmax(generatrix_lengths) + 1:
            ax.plot([0, x], [0, y], 'g-', label=f'L_max={L_max:.2f}')

    # Настройка графика
    ax.set_aspect('equal')
    ax.grid(True)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title(f'Развёртка наклонного конуса (пирамида с {N} гранями)\nD={D}, H={H}, α={alpha}°')
    ax.legend()

    # Отображение графика
    plt.show()

    return theta_total, generatrix_lengths, L_min, L_max


if __name__ == "__main__":
    try:
        # Параметры
        D = 794
        H = 1378.58
        alpha = 16.12305026  # Фиксированное значение alpha

        # Построить развёртку
        theta, generatrix_lengths, L_min, L_max = build_cone_sweep(D=D, H=H, alpha=alpha, N=12)
        print(f"Угол α: {alpha:.2f}°")
        print(f"Угол сектора: {math.degrees(theta):.2f} градусов")
        print(f"Минимальная образующая: {L_min:.2f}")
        print(f"Максимальная образующая: {L_max:.2f}")
    except ValueError as e:
        print(f"Ошибка: {e}")
