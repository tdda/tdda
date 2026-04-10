class URI:
    TDDASERIAL = 'http://tdda.info/ns/tdda.serial'
    CSVW = 'http://www.w3.org/ns/csvw'


class TDDASERIAL:
    name = 'tdda.serial'
    key = name
    ext = '.serial'
    version = '0.1'
    writer = f'tdda.serial-{version}'
    URI = URI.TDDASERIAL
    format = f'{URI}/{version}'
