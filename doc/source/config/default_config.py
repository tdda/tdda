from tdda.config import Config

print('DEFAULT')
dconfig = Config(load=False)
print(str(dconfig))

print('\n\n\n\n')
print('CURRENT')
cconfig = Config(load=True)
print(str(cconfig))



