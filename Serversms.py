#iniciamos el codigo
import serial
import time
import sys
import mysql.connector
from curses import ascii

idSqlGlobal="0"
ContSMS=0
def iniciarModen():
    # Enviamos un reset al modem
    sSerie.write("ATZ\r\n")
    print sSerie.readline()
    time.sleep(2)
    sSerie.write('AT+CPMS="SM","SM","SM"\r\n')
    print sSerie.readline()
    time.sleep(2)
    sSerie.write("AT+CMGF=1\r\n")
    print sSerie.readline()
    time.sleep(2)
    sSerie.write("AT+CMGD=0,34\r\n")
    print sSerie.readline()
    time.sleep(2)
    sSerie.write("AT+CSCA=\"+51190000000\"\r\n")
    print sSerie.readline()
    time.sleep(2)

def executeSQL(sql):
    try:
        cur.execute(sql)
        idSqlGlobal=str(cur.lastrowid)
        conn.commit()
    except NameError as e:
        conn.rollback()
        print "Error " + e
        
def enviarSMS(telf,iddb,Resultado):
    try:
       
       # Le ponemos en modo para SMS
        sSerie.write("AT+CMGF=1\r\n")
        time.sleep(.4)
        sSerie.write("AT+CSCA=\"+51190000000\"\r\n")
        time.sleep(.4)
        #print(sSerie.readline()) 
        # Le pasamos el numero al que vamos ha mandar el SMS
        sSerie.write("AT+CMGS=\"" +telf+"\"\r\n")
        time.sleep(.4)
        # Texto del mensaje terminado en Ctrl+Z
        sSerie.write(iddb + " "+ Resultado + "\r\n"  + ascii.ctrl('z'))
        print sSerie.readline()
        print "SMS enviado"
        # Leemos la informacion devuelta
        time.sleep(.2)
        resp=sSerie.readline()
        resp=resp.strip()
        if(resp!="OK"):
            time.sleep(.2)
            resp=resp + sSerie.readline()
            resp=resp.strip()
        time.sleep(1)
        print "Envio SMS:" + resp
        if resp=="OK":
            try:
                sqlu="UPDATE smslog SET F_Respuesta=now(),Estado='Enviado',Resultado='"+ Resultado + "' WHERE idSMS='"+ iddb +"'"
                cur.execute(sqlu)
                conn.commit()
                print "FIN: Se envio SMS con exito"
            except:
                conn.rollback()
                print "Error al actualizar en la base"
        else:
            print "FIN de proceso, No se pudo enviar respuesta...!!!"
    except ValueError:
        print ("Oops! se ha producido un error ...")
#Iniciamos el sismta    
#sSerie = serial.Serial('/dev/ttyUSB4', 460800)  # esta linea es para LINUX
PortCom=sys.argv[1]  # Aqui recepcionamos el puerto que necesitamos abrir
print ("Abriendo el puerto: " + PortCom)
sSerie = serial.Serial(PortCom, 9600,timeout=1)
sSerie.isOpen()
iniciarModen()
while True:
    sSerie.write("AT+CMGL=\"REC UNREAD\"\r\n")
    req=sSerie.readline()
    req=req.strip()
    if len(req)>50:
        ContSMS=ContSMS+1
        if req.find(",\"REC UNREAD\",\"+51") > 0:
            req=req.replace("\"","")
            req=req.replace("\n","|")
            req=req.replace("|","",1)
            msg=req.split('|')
            time.sleep(.4)
            print msg[0] + "\r\n"
            smsHead=msg[0]
            msg=smsHead.split(',') # fraccionar el mensaje
            idsmsa=msg[0]
            NroCelular=msg[2]
            idsmsaa=idsmsa.split(":")   #obtener id del sms
            idsms=idsmsaa[1].strip()
            smsBody=sSerie.readline()
            print ("Mensaje:" + smsBody + "\r\n")
            if smsBody.find("aave") >= 0:
                #convertir los datos sms a array
                smsB=smsBody.split(",")
                fecha=msg[4].replace("/","-")
                fhora=fecha + " " + msg[5][0:8]
                LongX=str(smsB[1]) 
                LatY=str(smsB[2])
                conn = mysql.connector.connect(host='10.10.10.10',user='user',passwd='pasxxx',db='dbUser')
                cur=conn.cursor(buffered=True)

                #verificar si existe el Nro celular en la base de datos
                sql_v="SELECT Nombre FROM sms_wlist WHERE NroCelular='" + NroCelular +"'"
                try:
                    cur.execute(sql_v)
                    conn.commit()
                except NameError as d:
                    conn.rollback()
                    print "Error: " + str(d)
                ValUsuario=cur.rowcount
                if ValUsuario==1:
                    if (LongX=="0.0") or (LatY=="0.0"):
                        sql="INSERT INTO smslog(Servicio,NroCel,Log_x,Lat_y,smsRecibido,F_Recibido,Fsistema) VALUES('" + smsB[0] + "','" + NroCelular + "','" + LongX + "','" + LatY + "','" + smsBody+"','" + fhora + "',now())"
                        executeSQL(sql)
                        enviarSMS(NroCelular,idSqlGlobal,"Log:0 Lat:0 No se pudo realizar la consulta")
                    else:    
                        #insertar sms en la base de datos
                        try:
                            sql="INSERT INTO smslog(Servicio,NroCel,Log_x,Lat_y,smsRecibido,F_Recibido,Fsistema) VALUES('" + smsB[0] + "','" + NroCelular + "','" + LongX + "','" +LatY + "','" + smsBody + "','" +fhora + "',now())"
                            cur.execute(sql)
                            idbd=str(cur.lastrowid)
                            print ("Mensaje insertado a la BD con id:" + str(idbd) + "\r\n")
                            conn.commit()
                        except NameError as e:
                            conn.rollback()
                            print "Error " + e
                        #enviar consulta al store procedure
                        resultado=""
                        try:
                            sqla=cur.callproc("sms_request",(smsB[1],smsB[2]))
                            print ("Llamada al store procedure " + smsB[1] + "," +smsB[2])
                            for result in cur.stored_results():
                                resultado = result.fetchall()
                            Respuesta=str(resultado[0][0])    
                            print ("Respuesta de StoreProcedure:" + Respuesta)
                            conn.commit()
                        except NameError as e:
                            conn.rollback()
                            print "Error " + e
                        # Enviamos un reset al modem
                        enviarSMS(NroCelular,idbd,Respuesta.strip())
                        #print ("FIN")
                else:
                    sql="INSERT INTO smslog(Servicio,NroCel,Log_x,Lat_y,smsRecibido,F_Recibido,Fsistema,Estado) VALUES('" + smsB[0] + "','" + NroCelular + "','" + LongX + "','" + LatY + "','" + smsBody+"','" + fhora + "',now(),'NoRegist')"
                    executeSQL(sql)
                    print "Usuario no encontrado: No se envia respuesta....\r\n"
                conn.close()        
        else:
            print "No entro: " + req
    if ContSMS>25:
        iniciarModen()
        ContSMS=0
