"""
Created on Mar 15, 2016

@author: zimmer
"""
import logging
from time import ctime
from datetime import datetime
from DmpWorkflow.core.models import Job, MAJOR_STATII, db
from DmpWorkflow.core.datacat import DataSet, DataFile, DataReplica
from os.path import basename, splitext, dirname

log = logging.getLogger("core")


def update_status(JobId, InstanceId, major_status, **kwargs):
    """ method to connect to db directly, without requests, i.e. should be run from server-side. """
    db.connect()
    log.debug("calling update_status: %s %s status:%s", JobId, InstanceId, major_status)
    my_job = Job.objects.filter(id=str(JobId))
    if not len(my_job):
        log.exception("update_status: could not find jobId")
        return
    my_job = my_job[0]
    assert major_status in MAJOR_STATII
    jInstance = my_job.getInstance(InstanceId)
    # print jInstance
    my_dict = {"last_update": ctime()}
    my_dict.update(kwargs)
    for key, value in my_dict.iteritems():
        jInstance.__setattr__(key, value)
    # finally, update status
    jInstance.setStatus(major_status)
    # print 'calling my_job.save'
    my_job.update()
    log.debug("updated job")
    return

def register_dataset(**kwargs):
    """ 
        all calls are handled through keywords in this method
        code will try to guess the DataSetName/DataFileName from the full file name, 
        unless it is specifically provided as additional keyword.
        KEYWWORDS
          prefix  : will be stripped from the filename to determine the DataSetName
          FileName: the full file name
          TStart  : Format YYYYMMDDHHMMSS
          TStop   : same as above
          Origin  : this one should be a dictionary: filename & site name (or a valid DataReplica instance!
          Gti     : good time interval, if TStop - TStart << Gti or >> Gti, a warning is shown
          DataType: USR, MC, OBS or BT
          DataClass: type of data 2A, 1F, Reco / Simu / Digi
          Release : release tag
          DataSetName: optional, if provided, will use this one
          DataFileName: same as above.
    """
    
    defaultTime = "19000101000000"
    prefix = kwargs.get("prefix","root://grid05.unige.ch:1094//dpm/unige.ch/home/dampe")
    FileName = kwargs.get("FileName",None)
    if FileName is None: 
        log.error("must provide at least a file name!")
        return
    TStart = datetime.strptime(kwargs.get("TStart",defaultTime),"%Y%m%d%H%M%S")
    TStop =  datetime.strptime(kwargs.get("TStop",defaultTime),"%Y%m%d%H%M%S")
    Gti   = float(kwargs.get("Gti",0.))
    delta = 1e3*(TStop - TStart).total_seconds()
    if (Gti <= 0.9*delta or Gti >= 1.1*delta):
        log.warning("GTI is siginificantly offset from TStop - TStart calculation for %s",FileName)
    DataType= kwargs.get("DataType","USR")
    DataClass=kwargs.get("DataClass","None")
    Release  =kwargs.get("Release","None")
    ChkSum   =kwargs.get("CheckSum",None)
    Origin   =kwargs.get("Origin",{})
    # try to guess dataset name
    Site = kwargs.get("Site","UNIGE")
    Status=kwargs.get("Status","New")
    pure_file_name = basename(FileName)
    DataSetName = kwargs.get("DataSetName",None)
    DataFileName= kwargs.get("DataFileName",None)
    FileType = kwargs.get("FileType",None)
    if DataFileName is None:
        DataFileName, FileType = splitext(pure_file_name)
    if DataSetName is None:
        DataSetName = dirname(FileName.replace(prefix,""))
        if DataSetName.startswith("/"): 
            DataSetName = DataSetName.split("/")[1]
        else: DataSetName.split("/")[0]
    
    # let's try to register some datasets
    ds = df = None
    try:
        ds = DataSet.objects.filter(name=DataSetName,DataType=DataType, release=Release, DataClass = DataClass)
    except DataSet.DoesNotExist():
        ds = DataSet(name=DataSetName,DataType=DataType, release=Release, DataClass = DataClass)
    df = ds.findDataFile(register=True,FileName=DataFileName,FileType=FileType,TStart=TStart, TStop=TStop, GTI=Gti)    
    if isinstance(Origin,DataReplica):
        df.declareOrigin(Origin)
    else:
        raise NotImplementedError("only supporting Origin as DataReplica instance for now.")
            
            
    
    
    df.registerReplica(path=FileName,status=Status)
    