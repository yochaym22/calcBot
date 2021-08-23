import re
import datetime

text = '2021-08-22 00:50:50.451116'
date = datetime.datetime.strptime(text, '%Y-%m-%d %H:%M:%S.%f')
# print(date)


def yield_valid_dates(text):
    for match in re.finditer(r"\d{1,2}[-,.]\d{1,2}[-,.]\d{4}", text):
        try:
            datetime.datetime.strptime(match.group(0), "%m.%d.%Y")
            yield match.group(0)
            # or you can yield match.group(0) if you just want to
            # yield the date as the string it was found like 05-04-1999
        except ValueError:
            # date couldn't be parsed by datetime... invalid date
            pass


testStr = """12-04-1999 here is some filler text in between the two dates 4-5-2016 then finally an invalid
 date 12.30.2016 here is also another invalid date, there is no 32d day of the month 6-32-2016. You can also not
 include the leading zeros like 4-2-2016 and it will still be detected"""

for date in yield_valid_dates(testStr):
    print(date)
