import yaml
import re
from mtypes import Data_db
from snap7.types import Areas


'''
# Area ID
class Areas(Enum): 
    PE = 0x81 PA = 0x82 MK = 0x83 DB = 0x84 CT = 0x1C TM = 0x1D
'''
patterns={
            'dbx':r'^db([0-9]+)\.dbx([0-9]+\.[0-9]+)',
            'dbb':r'^db([0-9]+)\.dbb([0-9]+)',
            'dbw':r'^db([0-9]+)\.dbw([0-9]+)',
            'dbd':r'^db([0-9]+)\.dbd([0-9]+)',
            'm':r'^m([0-9]+\.[0-9]+)',
            'i':r'^i([0-9]+\.[0-9]+)',
            'q':r'^m([0-9]+\.[0-9]+)',
}

class Myaml:
    def __init__(self, data_file):
        self.file=data_file
        self.data=None
        with open(data_file) as f:
            self.data=yaml.load(f, Loader=yaml.FullLoader)
    
    def parse(self):
        items=[]
        if self.data is None:
            return None
        devices=list(self.data.keys())
        for device in devices:
            values=self.data[device]
            for k,v in values.items():
                v1,v2,v3=v.lower().strip().split(',')
                area=Areas.DB
                dbnumber=0
                size=1
                bit_pos=-1
                is_db=False
                #print(k)
                name=k
                
                if 'dbx' in v1:
                    pattern=patterns['dbx']
                    is_db=True
                elif 'dbb' in v1:
                    pattern=patterns['dbb']
                    is_db=True
                elif 'dbw' in v1:
                    pattern=patterns['dbw']
                    size=2
                    is_db=True
                elif 'dbd' in v1:
                    pattern=patterns['dbd']
                    is_db=True
                    size=4
                elif 'm' in v1:
                    pattern=patterns['m']
                    area=Areas.MK
                elif 'i' in v1:
                    area=Areas.PE
                    pattern=patterns['i']
                elif 'q' in v1:
                    pattern=patterns['q']
                    area=Areas.PA
                else:
                    print('不支持的格式 %s', v1)
                    
                match=re.findall(pattern,v1)
                # 格式错
                if not match:
                    print('error:%s,%s 格式错误' % (pattern,v))
                    continue
                # 填db
                else:
                    # print('%s:%s' % (v,match))
                    d=device
                    if is_db:
                        dbnumber=match[0][0]
                        start=match[0][1]
                        if '.' in start:
                            start,bit_pos=start.split('.')
                    else:
                        start=match[0]
                        # 分割小数点
                        try:
                            start,bit_pos=start.split('.')
                        except ValueError:
                            print('value error',v,match)
                    #delay 检查
                    if v3 not in ['10ms','20ms','50ms','100ms','1s']:
                        v3='100ms'
                    items.append(Data_db(device,name,v1,area,int(dbnumber),int(start),v2,v3,int(size),int(bit_pos)))
                    
        return items
        
        
if __name__=='__main__':
    m=Myaml('c:/Users/y/Desktop/v12.yaml')
    rs=m.parse()
    for r in rs:
        print(r.address)
        