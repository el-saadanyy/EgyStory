from decimal import Decimal

def format_progress(total, target):
    progress = (total / target) * 100
    if progress >= 100:
        return 100
    elif progress == 0:
        return 0
    elif progress < 1:
        return round(float(progress), 3)
    else:
        if progress % 1 == 0:
            return int(progress)
        return round(float(progress), 1)

print("0/100:", format_progress(Decimal('0'), Decimal('100')))
print("5000/300000000:", format_progress(Decimal('5000'), Decimal('300000000')))
print("1000000/300000000:", format_progress(Decimal('1000000'), Decimal('300000000')))
print("12.5/100:", format_progress(Decimal('12.5'), Decimal('100')))
print("50/100:", format_progress(Decimal('50'), Decimal('100')))
print("100/100:", format_progress(Decimal('100'), Decimal('100')))
