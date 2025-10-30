# my_set = set()

# my_set.add(1)
# my_set.add(1)
# my_set.add(12)

# print(my_set)
import re
st = "Hi there I am india"
t = "there"
new_st = re.sub(t, "?", st, flags=re.IGNORECASE)
print(new_st)