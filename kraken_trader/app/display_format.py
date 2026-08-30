from decimal import Decimal,InvalidOperation
import re
_NUMERIC_TEXT=re.compile(r'^[-+]?\d+(?:\.\d+)?$')
def display_number(value,decimals=None):
 if value is None or isinstance(value,bool):return value
 try:number=Decimal(str(value))
 except (InvalidOperation,ValueError,TypeError):return value
 if not number.is_finite():return str(value)
 a=abs(number)
 if decimals is None:
  if a==0:p=0
  elif a>=Decimal('1'):p=2
  elif a>=Decimal('.1'):p=4
  elif a>=Decimal('.01'):p=6
  elif a>=Decimal('.001'):p=7
  elif a>=Decimal('.0001'):p=8
  else:p=8
 else:p=max(0,int(decimals))
 text=f'{number:.{p}f}'.rstrip('0').rstrip('.')
 if text in ('-0',''):text='0'
 return text.replace('.',',')
class DisplayFloat(float):
 def __new__(cls,value):return super().__new__(cls,float(value))
 def __str__(self):return display_number(float(self))
 def __repr__(self):return str(self)
class DisplayNumberText(str):
 def __str__(self):return display_number(super().__str__())
 def __repr__(self):return str(self)
def display_tree(value):
 if isinstance(value,dict):return {k:display_tree(v) for k,v in value.items()}
 if isinstance(value,list):return [display_tree(v) for v in value]
 if isinstance(value,tuple):return tuple(display_tree(v) for v in value)
 if value is None or isinstance(value,bool):return value
 if isinstance(value,(float,Decimal)):return DisplayFloat(value)
 if isinstance(value,str) and _NUMERIC_TEXT.fullmatch(value.strip()) and '.' in value:return DisplayNumberText(value.strip())
 return value
