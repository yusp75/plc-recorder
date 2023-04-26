# 数据库
from peewee import *
from datetime import datetime, timedelta
from itertools import groupby
import snap7

db = SqliteDatabase('yu.db',pragmas={'journal_mode': 'wal','cache_size': -1024 * 128})

class Data(Model):
    device=CharField() #0
    name=CharField() #1
    addr=CharField() #2
    bit_pos=IntegerField() #3
    raw_value=CharField() #4
    value=CharField() #5
    data_type=CharField() #6
    time=DateTimeField(default=datetime.now()) #7
    
    class Meta:
        database=db


class Db:
    def __init__(self):
        self.db=db
        self.db.create_tables([Data,])
        
    def save(self, *arg):
            device=arg[0]
            name=arg[1]
            addr=arg[2]
            bit_pos=arg[3]
            raw_value=arg[4]
            value=arg[5]
            data_type=arg[6]
            dt=datetime.now()
            
            d1=Data(device=device, name=name, addr=addr,bit_pos=bit_pos,raw_value=raw_value,value=value,data_type=data_type,time=dt)
            d1.save()
            
    def close(self):
        self.db.close()
   
    def query(self,dt1,dt2,fields):
        #lambda for python_value
        convert_value=lambda vv: [float(v) if '.' in v else int(v) for v in vv.split(',') if v]
        convert_time=lambda tt: [datetime.strptime(t,'%Y-%m-%d %H:%M:%S.%f').timestamp() for t in tt.split(',') if t]
        data_value = (fn
            .GROUP_CONCAT(Data.value)
            .python_value(convert_value))
        data_time = (fn
            .GROUP_CONCAT(Data.time)
            .python_value(convert_time))
        #分组查询     
        qs=(Data
        .select(Data.name,Data.data_type,data_value.alias('values'),data_time.alias('times'))
        .where((Data.name.in_(fields)) & (Data.time.between(dt1,dt2)))
        .group_by(Data.name)
        .order_by(Data.time))
        print('query, size:%d\n' % len(qs),fields)
        
        names=[]
        data=[]
        for q in qs:
            #print(q.name, q.values,q.times)
            names.append(q.name)
            #data.append({q.name:(q.times,q.values),'dtype':q.data_type})
            data.append({'nm':q.name,'tm':q.times,'v':q.values,'t':q.data_type})
        #view sql
        #print(qs)
        return set(names),data
  
    # 转换数据库字符串值
    def cal_q(self,q):        
        xv=bytearray(q.value.encode(encoding='utf_16_be'))
        #bool
        if q.data_type=='bool':  
            #utf_16_be 将1字节编码为2字节
            xv=1 if snap7.util.get_bool(xv,1,q.bit_pos) else 0
        #word
        if q.data_type=='word':
            xv=snap7.util.get_int(xv,0)
        #int
        if q.data_type=='int':
            xv=snap7.util.get_dint(xv,0)
        #real
        if q.data_type=='real':
            xv=snap7.util.get_real(xv,0)
        return xv,int(q.time.timestamp()) #x,y
            
   
if __name__=='__main__':
    db=Db()
    db.save('a1','u1','db127.dbx1.0',0,'1',datetime.now())
    dt2=datetime.now()
    dt1=dt2+timedelta(hours=-1)
    print(dt1,dt2)
    db.query(dt1,dt2)
        