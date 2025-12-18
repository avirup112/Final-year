from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import smtplib
import redis.asyncio as redis
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
import os
import asyncio
from enum import Enum
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Global instances
redis_client = None

class NotificationType(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationRequest(BaseModel):
    type: NotificationType
    priority: Priority = Priority.MEDIUM
    subject: str
    message: str
    recipients: List[str]
    metadata: Dict[str, Any] = {}

class EmailNotification(BaseModel):
    to: List[EmailStr]
    subject: str
    body: str
    html_body: Optional[str] = None
    priority: Priority = Priority.MEDIUM

class WebhookNotification(BaseModel):
    url: str
    payload: Dict[str, Any]
    headers: Dict[str, str] =0)port=801", .0.0, host="0.0(app uvicorn.run  uvicorn
 ort ":
    impmain__"__ame__ == e

if __n   rais)
     : {e}"ficatione notieud to qule"Faigger.error(f   loe:
     ption as ept Exce   exc        
 ")
name}} in {queue_n_idtioican {notificatioed notifueuf"Qo(logger.inf
           
      # 24 hoursdata)) (status_, json.dumpss_key, 86400tatunt.setex(sredis_cliewait      a"
   id}ification_atus:{not_stonficatinotius_key = f"at      st        

  
        }pts": 0  "attem        ,
  soformat().itcnow()time.u": dateted_at    "crea    
    eued","qu": tatus        "s_id,
    otification_id": nonificatinot   "
         ata = {_d    statuss
    tution stare notifica    # Sto     
     lt=str))
  e, defaudumps(messagame, json.sh(queue_nt.lpuedis_clienawait r
                       }
 ata
ation_dotific*n           *
 id,n_otificatio_id": notification"n         {
    e =     messagqueue
   priority o  t       # Add
 
        "ority}ons_{prinotificati" f_name =   queue   ium")
  "med, rity"rio"pet(data.gification_= notity   priorry:
       tg"""
   ssinprocekground ion for bacatueue notific  """Qy]):
  Dict[str, Anon_data: tificatitr, noion_id: s(notificattificationueue_noync def q
asep(5)
sle asyncio. await           e}")
ing error: {essueue proccation qf"Notifior(logger.err         
    e:xception asexcept E  
                  eep(1)
    cio.sl  await asyn     
         rocessed: p     if nots
       es procs toonatiotific  # No n
               k
       brea                    ed = True
     process            n)
   notificatioon(ficatinotis_single_oces   await pr                
                 _data)
    (messageoads json.lication =      notif            ult
  ata = resage_d, mess  _                t:
      if resul        t=1)
    name, timeoueue_op(qubrpent.dis_clit re awai  result =          
    en from queuicationotif Get     #                 
   "
        rity}rioons_{ptificati= f"noname ueue_         q       s:
prioritiety in queue_ for priori      rder
     ity oues in priorProcess que       #  
     
           Falseed =    process       try:
          e True:
 
    whil]
   ", "low"medium"", "high ritical","c= [riorities queue_p)
    processor" queue notificationg in("Startfoin   logger."
 "" queuescationnotifirocess  pd task to""Backgroun"    :
ue()fication_ques_notic def processyn
ar(e))
iled", ston_id, "fanotificati_status(ficationotiait update_n
        aw failedus toUpdate stat #        d}: {e}")
ation_in {notificcatioess notifi proced toFailer.error(f"logg     
   n as e:ioxcept   except E   
 )
     on_id}"otificati{nn  notificatiossfully sentSuccer.info(f"    loggeNone)
    , "sent", ation_idotifics(ntustatification__noate updwait
        aus to sentte stat     # Upda  
   turn
               ree}")
   cation_typ {notifie:fication typUnknown notining(f"arlogger.w           e:
         els"])
tation["datificawebhook(noit send_  awa      
    ":= "webhookon_type =catiif notifi     el  
 )ta"]tion["datificaemail(nod_ait sen    aw      il":
  "ema= _type =otificationf n
        i        }")
tion_typecaype {notifion_id} of tnotificatition { notifica"Processing(fogger.info       l
    try:
  
   ]ype"["tficationpe = notin_tytificatio
    no_id"]ficationation["notid = notificion_iificat    not
"""ionle notificat sing"Process a:
    "" Any])ct[str,ication: Diotification(nsingle_notifprocess_f 

async dee rais        {e}")
nd webhook: seed toilrror(f"Fa    logger.e:
    ion as eExceptpt ceex 
           }")
l']ook_data['ur to {webhebhook sentnfo(f"Wlogger.i              
 )
 or_status(_faise response.r                    )
})
   ders', {heaa.get('webhook_dat headers=        
       load'],a['payhook_datson=web  j             
 a['url'],ebhook_dat    w     
       client.post(t waie = a    respons     
   :ient cl) asmeout=30.0(tiClientyncAspx.ttc with h  asyn:
      
    tryion"""icatook notifbh""Send we  ", Any]):
  t[strata: Dick_doobhook(webhwed_ef senc dyn
asaise
 r      
  {e}")l:end emaied to sror(f"Failger.er     log as e:
   t Exception    excep    
")
    'to']}ata[ail_dt to {em"Email senfo(f.ingger
        lo    (msg)
    ssage.send_me   server)
         TP_PASSWORDER, SMogin(SMTP_US  server.l        
  .starttls() server         ver:
  ) as serP_PORTHOST, SMTMTP(SMTP_.Splib  with smt      email
Send  #     
    
       t)l_partmach(hmsg.att          'html')
  ml_body'], ta['htext(email_da MIMETpart =      html_  dy'):
    tml_bodata.get('h if email_ded
       ody if provi# Add HTML b 
        
       t)(text_parchsg.atta       m 'plain')
 a['body'],email_datIMEText(t = Mxt_par        text body
 te   # Add 
     
       data['to'])oin(email_ = ', '.j'To'] msg[      SER
 MTP_U['From'] = S        msgubject']
l_data['s = emaig['Subject']       ms)
 ternative''alMEMultipart( MImsg =
         messagereate        # C   try:
)
    
 ured"s not configntialP crede"SMTn(ceptio    raise ExSWORD:
    ot SMTP_PAS or not SMTP_USER    if nTP"""
sing SMSend email u"
    ""r, Any]):ata: Dict[stl_dmaiil(e_emaf senddenc ")

asyus: {e} statnotificationo update ed t"Failer.error(f logg      as e:
 ion  Except   except   
 str))
      default=tus_data,mps(sta json.du0,, 8640s_keyx(statuetelient.sis_c redit       awars)
 houus (24 dated stat up  # Store
              
", 0) + 1mptsget("atteta.= status_da"] "attemptsata[_dtus         staerror)
   or"] = str(_data["err      statusor:
          if err 
    ()
       .isoformat.utcnow() datetimesent_at"] =tus_data["       sta
     == "sent": status if  
            
   })      at()
 ).isoformtcnow(: datetime.udated_at" "up         
  ": status,    "status  {
      .update(data   status_tus
     # Update sta           
    }
            pts": 0
 tem"at               ation_id,
 ": notification_idicif"not          
       = { status_data   :
          else      nt_status)
rreds(cu json.loa =s_datatatu s        
   nt_status: if curre     y)
  us_ke.get(statdis_clientait reatus = aw  current_st     tatus
 t current s     # Ge  
   "
      n_id}catiotus:{notifification_staey = f"noti_k      status  ry:
"
    t"on status"tificatinoate pd   """Une):
 No = tional[str]: Oprror, eatus: strr, stid: station_fic_status(notitionficaupdate_noti
async def 
=str(e))0, detailode=50s_ction(statuTPExcep    raise HT
    ion as e:ceptpt Ex    exce
  }()
      soformate.utcnow().idatetimimestamp":      "t       )),
lues(ts.vaum(sta": seuedquotal_   "t          stats,
ats": "queue_st     {
      turn  re 
             _length
 ty] = queuepriori     stats[)
       n(queue_nament.llelie redis_cngth = await queue_le      "
     iority}ons_{pratif"notifice =    queue_nam  "]:
       lowum", "h", "medical", "hig"critiy in [or priorit      f     
  
    {}stats =y:
            tr"""
isticsstatation queue et notific""G "):
   queue_stats(c def get_)
asynue/stats""/queapp.get()

@etail=str(e)ode=500, dstatus_cxception(TTPE H    raisee:
    on as pt Excepti   exces_data)
 .loads(statueturn json      r 
  ")
       not foundotification , detail="Ne=404odtus_cstation(TTPExcepraise H          a:
  s_datot statuif n              
 
 atus_key).get(stedis_client= await ratus_data    st    
 id}"ion_s:{notificattatufication_sey = f"noti    status_kry:
       t""
 tatus"ification s""Get not    "):
 stration_id:fictitus(noion_stacatget_notifiync def id}")
asion_tificat/status/{no.get(")

@app(e) detail=str500,status_code=n(eptioHTTPExc  raise )
      rt: {e}"tem alesysd ed to senor(f"Failerr     logger.
    as e:Exceptionexcept   }
    )
      at(ow().isoforme.utcn: datetimat""created_    e,
        valuverity. se": "severity
           ,"queued"tatus":       "s  pe,
    tye": alert_typrt_      "ale    id,
  fication_": noti_idication "notif          
 urn {et    r     
       })
       oformat()
 .utcnow().isme: datetitamp"     "times,
       ice_nameerv: s"ame_n "service          
 cation_id,fiid": notitification_"no        ta,
    daail_     **em     on_id, {
  icatication(notifeue_notifiwait qu    a
    processingtion for icaueue notif    # Q  
          
        }
       }     ue
rity.val: severity"    "prio         }",
   : {message\nMessagee}y.valueveritrity: {sme}\nSeveice_na: {servf"Servicey":     "bod          ",
  e}ert_typt: {alertem Al": f"Sys"subject                in_emails,
o": adm         "t       ta": {
        "da    email",
"type": "     {
       _data =      email       
   ils
 dmin emanfigure a# Cocom"]  to-system.ryp@c = ["adminmails    admin_eails
     eminfigure adm     # Con  try:
   
    
  %f')}"S__%H%M%m%dtrftime('%Y%).sow(cntetime.utdart_{"aleon_id = f notificatin"""
   notificatiostem alert ""Send sy "   :
EDIUM
)ity.M= Priority rioreverity: P
    se: str,amservice_n  tr,
   message: s    str,
pe:alert_ty   t(
 _alertemdef send_sys
async ")lertem-a"/send/syst(.post))

@apptail=str(eode=500, de_cstatusTPException(ise HT      ra  {e}")
fication:  notibhookweueue led to qai"Fger.error(f        loge:
as eption xcept Exc e
   
        }ty.valueion.prioricat: notifirity"rio    "p    (),
    rmatcnow().isofome.utat": datetited_crea  "        
  ",": "queued   "status
         ion_id, notificat":ation_id  "notific   {
        return    
                    })
format()
w().isotetime.utcnoted_at": da"crea       _id,
     tion: notificaon_id""notificati        
    ity.value,ation.priory": notificriorit "p        ict(),
   tion.d": notifica      "data,
      k""webhoo: "type"         
   tion_id, {caation(notifific queue_notiwait        asing
esproction for notifica # Queue      
    
    try:
  %S_%f')}"%d_%H%Mime('%Y%m().strftnowtetime.utcdaok_{"webho fication_id =tifno"""
    onatificwebhook noti"Send  ""
   ):ksroundTasks: Backgound_tason, backgratiookNotificebh Wn:ficatioation(notiificotok_n_webhoef send")
async dwebhooknd/ost("/se
@app.pl=str(e))
=500, detaiodeon(status_cPExceptise HTT     rai")
   ation: {e}mail notific to queue ef"Failedror(.er   logger:
     tion as et Excepcep   ex   }
      lue
.priority.vaation": notificoritypri  "         
 mat(),for).isonow(atetime.utcd_at": date      "cre",
       "queued":tatus  "s
          cation_id,": notifin_idficatio"noti           
 urn {        ret    
   })
    at()
     formw().isome.utcnoat": datetieated_     "cr      ation_id,
 ic: notifd"tification_i      "no
      e,riority.valu.pontinotifica": rity     "prio      ict(),
 cation.dtifi": nota        "daail",
    type": "em      "
      _id, {ficationcation(notiueue_notifi   await q    ocessing
 on for protificati n    # Queue      try:
  }"
    
%H%M%S_%f')%m%d_rftime('%Yutcnow().sttime.email_{dated = f"on_inotificati  on"""
  otificati nd email""Sen:
    "Tasks) Backgroundund_tasks:on, backgroificati EmailNotication:ation(notifotific_email_nsend def 
asyncmail")send/et("/pos
@app.tr(e))
, detail=s=503tus_codestaeption(xce HTTPE  rais
      s e:on apti Exce   except}
 
        now().utc datetimestamp":  "time        
  figured,": smtp_con_configured"smtp        ue,
    Tr": ctednes_conredi      "    ",
  cecation-servitifinorvice": "       "se",
     thys": "heal    "statu       
 rn {etu        r  
D)
      TP_PASSWORSER and SMSMTP_U = bool(nfigured  smtp_co()
      lient.ping_cisawait red
        
    try:"""ndpointck eh che""Healt:
    "th_check()ef heal")
async d"/health.get(ppwn")

@ashutdoon service "Notificati.info(    loggerse()
los_client.cawait redi:
        redis_client
    if """shutdownCleanup on ""
    "wn():ef shutdonc d
asydown")hutvent("sapp.on_eraise

@
        : {e}")viceseration otificialize nitled to in"Fairor(fr.er     logge as e:
   eptionxcept Exc  ey")
   successfullzedice initialition servNotificager.info("    log      
   ))
   on_queue(notificatiocess_k(prcreate_tas asyncio.sor
       procesn ficatiokground noti bacart     # St
   
        ient.ping()t redis_cl      awai  ue)
s=TresponseL, decode_rurl(REDIS_URis.from_t = redlienedis_c     r   :
   try    
 ce")
on serviatiicotiflizing n"Initiainfo(logger.client
    redis_bal     glo""
rvice"n senotificatioInitialize   """):
  rtup(def sta")
async uptartnt("sn_eve

@app.o: int = 0mptsne
    attetr] = Noptional[s Oror:
    erNone = e]timatetional[dsent_at: Op     str
s:tatu   sd: str
 tification_ino
    el):seModatus(BacationSts NotifilasUM

cMEDIty.ity = Priori Priority:  prior {}
  