import sys; sys.path.insert(0,'.')
from datetime import date
from ga_fiscal_core.params import load_from_yaml
from ga_fiscal_core.engine import compute, PayslipFacts
from ga_fiscal_core.exemptions import GainLine
Y='/home/ubuntu/odoo/extra-addon/docs/base_connaissance/parametres_fiscaux_gabon_2026.yaml'
BR=[(0,1500000,0,0),(1500001,1920000,5,75000),(1920001,2700000,10,171000),(2700001,3600000,15,306000),(3600001,5160000,20,486000),(5160001,7500000,25,744000),(7500001,11000000,30,1119000),(11000001,99999999,35,1669000)]
def v1(base,alw,indcnss,ncnss,part,t_sal=2.5,t_pat=16,t_fnh=2):
    brut=base+alw
    pcnss=min(brut+indcnss,1500000); pcam=min(brut+indcnss,2500000)
    cnss=t_sal*pcnss/100; cam=2*pcam/100; salc=cnss+cam
    tcs=max((brut-salc-150000)*0.05,0) if brut-salc-150000>0 else 0
    cimp=brut-tcs-salc; ab=min(cimp*0.2,833333)
    q=(cimp-ab)*12/part; k=0
    for lo,hi,t,d in reversed(BR):
        if lo<=q<=hi: k=q*t/100-d; break
    irpp=k/12*part; irpp=irpp if irpp>1000 else 0
    net=brut+indcnss+ncnss-(salc+tcs+irpp)
    fnh=t_fnh*pcnss/100; cfp=0.005*(brut-salc)
    return dict(cnss=cnss,cnamgs=cam,tcs=tcs,irpp=irpp,net=net,cnss_pat=t_pat*pcnss/100,fnh=fnh,cfp=cfp)
def v2(d,base,alw,indcnss,ncnss,marital,children):
    p=load_from_yaml(Y,d)
    lines=[GainLine('BASIC',base),GainLine('ALW',alw)]
    if indcnss: lines.append(GainLine('IND',indcnss,None,'EXEMPT'))
    if ncnss: lines.append(GainLine('NC',ncnss,'EXCLUDED','EXEMPT'))
    r=compute(PayslipFacts(lines=tuple(lines),marital=marital,children=children),p)
    return dict(cnss=r.cnss_employee,cnamgs=r.cnamgs_employee,tcs=r.tcs,irpp=r.irpp,net=r.net,cnss_pat=r.cnss_employer,fnh=r.fnh,cfp=r.cfp,parts=r.tax_parts)
cases=[(150000,0,0,0,'single',0,1),(300000,50000,20000,10000,'single',0,1),(590000,0,0,0,'married',2,3),(800000,100000,50000,0,'married',1,2.5),(2000000,300000,0,0,'single',0,1)]
for d in (date(2026,6,30),date(2026,9,30)):
  print('#### paramètres au',d)
  for c in cases:
    a=v1(*c[:4],c[6]); b=v2(d,*c[:6])
    print(c, 'parts V2',b.pop('parts'))
    for k in a: print(f'   {k:9} V1 {a[k]:>12,.0f}  V2 {b[k]:>12,.0f}  écart {b[k]-a[k]:>+10,.0f}')
