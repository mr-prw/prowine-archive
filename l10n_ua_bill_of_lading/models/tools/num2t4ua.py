# -*- coding: utf-8 -*-

import decimal


units = (
    'ноль',

    ('один', 'одна'),
    ('дві', 'два'),

    'три', 'чотири', "п'ять",
    'шість', 'сім', 'вісім', "дев'ять"
)

teens = (
    'десять', 'одинадцять',
    'дванадцять', 'тринадцять',
    'чотирнадцять', "п'ятнадцять",
    'шістнадцять', 'сімнадцять',
    'вісімнадцять', "дев'ятнадцять"
)

tens = (
    teens,
    'двадцять', 'тридцять',
    'сорок', "п'ятдесят",
    'шістдесят', 'сімдесят',
    'вісімдесят', "дев'яносто"
)

hundreds = (
    'сто', 'двісті',
    'триста', 'чотириста',
    "п'ятсот", 'шістсот',
    'сімсот', 'восімсот',
    "дев'ятсот"
)

orders = (
    (('тисяча', 'тисячі', 'тисяч'), 'f'),
    (('мільйон', 'мільйона', 'мільйонів'), 'm'),
    (('мільярд', 'мільярда', 'мільярдів'), 'm'),
)

minus = 'мінус'


def thousand(rest, sex):
    """Converts numbers from 19 to 999"""
    prev = 0
    plural = 2
    name = []
    use_teens = 10 <= rest % 100 <= 19
    if not use_teens:
        data = ((units, 10), (tens, 100), (hundreds, 1000))
    else:
        data = ((teens, 10), (hundreds, 1000))
    for names, x in data:
        cur = int(((rest - prev) % x) * 10 / x)
        prev = rest % x
        if x == 10 and use_teens:
            plural = 2
            name.append(teens[cur])
        elif cur == 0:
            continue
        elif x == 10:
            name_ = names[cur]
            if isinstance(name_, tuple):
                name_ = name_[0 if sex == 'm' else 1]
            name.append(name_)
            if 2 <= cur <= 4:
                plural = 1
            elif cur == 1:
                plural = 0
            else:
                plural = 2
        else:
            name.append(names[cur - 1])
    return plural, name


def num2text(num, main_units=((u'', u'', u''), 'm')):
    """
    http://ru.wikipedia.org/wiki/Gettext#.D0.9C.D0.BD.D0.BE.D0.B6.D0.B5.D1.81.\
    D1.82.D0.B2.D0.B5.D0.BD.D0.BD.D1.8B.D0.B5_.D1.87.D0.B8.D1.81.D0.BB.D0.B0_2
    """
    _orders = (main_units,) + orders
    if num == 0:
        # ноль
        return ' '.join((units[0], _orders[0][0][2])).strip()

    rest = abs(num)
    order = 0
    name = []
    while rest > 0:
        plural, nme = thousand(rest % 1000, _orders[order][1])
        if nme or order == 0:
            name.append(_orders[order][0][plural])
        name += nme
        rest = int(rest / 1000)
        order += 1
    if num < 0:
        name.append(minus)
    name.reverse()
    return ' '.join(name).strip()


def decimal2text(value, places=2,
                 int_units=(('', '', ''), 'm'),
                 exp_units=(('', '', ''), 'm')):
    value = decimal.Decimal(value)
    q = decimal.Decimal(10) ** -places

    integral, exp = str(value.quantize(q)).split('.')
    return u'{} {}'.format(
        num2text(int(integral), int_units),
        num2text(int(exp), exp_units))
