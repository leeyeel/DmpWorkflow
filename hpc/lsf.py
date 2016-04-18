'''
Created on Mar 23, 2016

@author: zimmer
'''
import hpc.batch
from utils.shell import run
# LSF-specific stuff

class BatchJob(hpc.batch.BatchJob):
    def submit(self,**kwargs):
        ''' each class MUST implement its own submission command '''
        extra = "%s"%self.extra if isinstance(self.extra,str) else None
        if isinstance(self.extra,dict):
            self.extra.update(kwargs)
            extra = "-%s %s".join([(k,v) for (k,v) in self.extra.iteritems()])

        cmd = "bsub -q %s -eo %s -R \"%s\" %s %s"%(self.queue, self.logFile, 
                                                   "&&".join(self.requirements), 
                                                   self.extra, self.command)
        self.__execWithUpdate__(cmd, "batchId")
        
    def kill(self):
        ''' likewise, it should implement its own batch-specific removal command '''
        cmd = "bkill %s"%self.batchId
        self.__execWithUpdate__(cmd, "status",value="Failed")
        
class LSF(hpc.batch.BATCH):
    keys = "USER,STAT,QUEUE,FROM_HOST,EXEC_HOST,JOB_NAME,"
    keys+= "SUBMIT_TIME,PROJ_NAME,CPU_USED,MEM,SWAP,PIDS,START_TIME,FINISH_TIME,SLOTS"
    keys = keys.split(",")
    status_map = {"RUN":"Running","PEND":"Submitted","SSUSP":"Suspended",
                  "EXIT":"Failed","DONE":"Completed"}
    
    def update(self):
        self.allJobs.update(self.aggregateStatii())
    
    def aggregateStatii(self,asDict=True,command=["bjobs -Wa"]):
        jobs = {}
        output = run(command)
        if not asDict: return output
        else:
            for i, line in enumerate(output.split("\n")):
                if i>0:
                    this_line = line.split(" ")
                    jobID = this_line[0]
                    this_line.remove(this_line[0])
                    while "" in this_line: this_line.remove("")
                    this_job = dict(zip(self.keys,this_line))
                    if len(this_job):
                        jobs[jobID]=this_job
            return jobs