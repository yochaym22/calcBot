s = 'abcde'
chars_to_replace = ['a', 'b', "'"]
for char in chars_to_replace:
    s = s.replace(char, '')
print(s)
