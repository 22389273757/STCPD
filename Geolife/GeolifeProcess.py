import joblib 
import numpy as np 
import datetime 
import os
from haversine import haversine
inputbasepath = r"OriginData"

outputbasepath = r''

lngmax=116.6
lngmin=116.15
latmin=39.75
latmax=40.1

label_transportmode_dict={"bus":"public","subway":"public","train":"public","car":"drive","taxi":"drive","bike":"bike","walk":"walk"}

distance_threshold = 2000 #m
time_threshold = 1200 #s
labelmatch_threshold = 300 #s
giveup_length = 10 # gps samplings

def loadtrajectory(inputpath):
    datalist = []
    fp = open(inputpath,encoding='utf-8')
    for line in fp:
        datalist.append(line.replace("\n","").split(","))
    datalist = datalist[6:]
    checkdatalist = []
    for data in datalist:
        curlng = float(data[1])
        curlat = float(data[0])
        daystr = np.array(data[-2].split("-"),dtype=int).tolist()
        timestr = np.array(data[-1].split(":"),dtype=int).tolist()
        datetimestr = daystr+timestr 
        curdate = datetime.datetime(*datetimestr)
        if curlng>lngmin and curlng<lngmax and curlat>latmin and curlat<latmax:
            checkdatalist.append([curlng,curlat,curdate])
    return checkdatalist 

def loadlabellist(inputpath):
    fp = open(inputpath)
    labellist = []
    newlabellist = []
    for line in fp:
        labellist.append(line.replace('\n',"").split("\t"))
    labellist = labellist[1:]
    for labelline in labellist:
        starttime = labelline[0]
        endtime = labelline[1]
        label = labelline[2]
        startstr = starttime.split(" ")
        endstr = endtime.split(" ")
        
        startdaystr = startstr[0].split("/")
        starttimestr = startstr[1].split(":")
        startdatetimelist = np.array(startdaystr+starttimestr,dtype=int).tolist()
        
        enddaystr = endstr[0].split("/")
        endtimestr = endstr[1].split(":")
        enddatetimelist = np.array(enddaystr+endtimestr,dtype=int).tolist()
        
        startdatetime = datetime.datetime(*startdatetimelist)
        enddatetime = datetime.datetime(*enddatetimelist)
        try:
            labelindex = label_transportmode_dict[label]
        except:
            labelindex = -1 
        
        newlabellist.append([startdatetime,enddatetime,labelindex])
    return newlabellist 

def trajectorysegment(datalist):
    segmentlist = []
    segmentpointlist = []
    for index in range(len(datalist)-1):
        curpoint = datalist[index]
        nextpoint = datalist[index+1]
        distance_interval = haversine(curpoint[:2], nextpoint[:2])
        time_interval = np.fabs((nextpoint[2]-curpoint[2]).total_seconds())
        if distance_interval>distance_threshold or time_interval > time_threshold:
            segmentpointlist.append(index+1)
    
    if len(segmentpointlist) == 0:
        return [datalist]
    
    segmentpointlist.insert(0,0)
    segmentpointlist.append(len(datalist))
    
    for index in range(len(segmentpointlist)-1):
        startindex = segmentpointlist[index]
        endindex = segmentpointlist[index+1]
        if (endindex-startindex)>2:
            segmentlist.append(datalist[startindex:endindex])
    return segmentlist     

def matchwithlabel(datalist,labellist):
    startdatetime = datalist[0][2]
    enddatetime = datalist[-1][2]
        
    # get trajectory start time label index
    startindex = 0
    startinterval = np.inf
    for index in range(len(labellist)):
        curinterval = np.fabs((startdatetime - labellist[index][0]).total_seconds())
#         if curinterval>=startinterval:
#             break 
        if curinterval<startinterval:
            startindex = index 
            startinterval = curinterval 

    # get trajectory end time label index
    endindex = 0
    endinterval = np.inf
    for index in range(len(labellist)):
        curinterval = np.fabs((enddatetime - labellist[index][1]).total_seconds())
        if curinterval<endinterval:
            endindex = index 
            endinterval = curinterval 
    
    segmentlabellist = labellist[startindex:endindex+1]
    
    for segmentlabel in segmentlabellist:
        if segmentlabel[-1] == -1:
            return "Unlabel"
    
    changepointindexlist = []
    for segmentlabel in segmentlabellist:
        startchangetime = segmentlabel[0]
        endchangetime = segmentlabel[1]
        transmodelabel = segmentlabel[2]
        
        startchangeindex = 0
        mintimeinterval = np.inf
        for index in range(len(datalist)):
            curtime = datalist[index][2]
            curinterval = np.fabs((curtime-startchangetime).total_seconds())
            if curinterval<mintimeinterval:
                startchangeindex = index 
                mintimeinterval = curinterval

        endchangeindex = 0
        mintimeinterval = np.inf 
        for index in range(len(datalist)):
            curtime = datalist[index][2]
            curinterval = np.fabs((curtime-endchangetime).total_seconds())

            if curinterval<mintimeinterval:
                endchangeindex = index
                mintimeinterval = curinterval            
        
        changepointindexlist.append([startchangeindex,endchangeindex,transmodelabel])
    
    trajectorylabellist = []
    for changeindex in changepointindexlist:
        labeldict = {}
        labeldict["start"] = changeindex[0]
        labeldict["end"] = changeindex[1]
        labeldict["transmode"] = changeindex[-1]
        trajectorylabellist.append(labeldict)

    
    if len(trajectorylabellist) == 0:
        return "Unlabel"
    
    if len(trajectorylabellist) == 1:
        labeldict = trajectorylabellist[0]
        if labeldict["start"] == 0 and labeldict["end"] == 0:
            return "Unlabel"
    
    return trajectorylabellist 

def mergetrajectorysegment(segmentlist):
    mergesegmentlist = []
    mergesegmentlist.append(segmentlist[0])
    for index in range(1,len(segmentlist)):
        cursegment = segmentlist[index]
        curtimestamp = cursegment[0][-1]
        
        lastsegment = mergesegmentlist[-1]
        lasttimestamp = lastsegment[-1][-1]
        
        curtimeinterval = np.fabs((curtimestamp-lasttimestamp).total_seconds())
        if curtimeinterval < time_threshold:
            mergesegmentlist[-1]+=cursegment 
        else:
            mergesegmentlist.append(cursegment)
    return mergesegmentlist
        
def cutunlabelsegment(datalist,trajlabellist):
    firstlabel = trajlabellist[0]
    segmentlength = firstlabel["start"]
    pretrajsegment = datalist[:segmentlength]
    datalist = datalist[segmentlength:]
    for trajlabel in trajlabellist:
        trajlabel["start"] = trajlabel["start"] - segmentlength 
        trajlabel["end"] = trajlabel["end"] - segmentlength
    lastindex = trajlabellist[-1]["end"]
    backtrajsegment = datalist[lastindex:]
    datalist = datalist[:lastindex]
    return pretrajsegment,backtrajsegment,datalist,trajlabellist 

def control():
    labeldatalist = []
    unlabeldatalist = []
    
    labeldataoutputpath = os.path.join(outputbasepath,"labeldata.pickle")
    unlabeldataoutputpath = os.path.join(outputbasepath,"unlabeldata.pickle")
    
    userlist = os.listdir(inputbasepath)
    for user in userlist:
        print(user)
        userpath = os.path.join(inputbasepath,user)
        trajectorybasepath = os.path.join(userpath,"Trajectory")
        trajectorynamelist = os.listdir(trajectorybasepath)
        curlabelpath = os.path.join(userpath,"labels.txt")
        
        if os.path.exists(curlabelpath):
            curlabellist = loadlabellist(curlabelpath)
            curtrajectorylist = []
            
            for trajectoryname in trajectorynamelist:
                inputpath = os.path.join(trajectorybasepath,trajectoryname)
                trajdatalist = loadtrajectory(inputpath)
                if len(trajdatalist)>1:
                    segmentlist = trajectorysegment(trajdatalist)
                    curtrajectorylist+=segmentlist
                    
            curtrajectorylist = mergetrajectorysegment(curtrajectorylist)
            for trajectory in curtrajectorylist:
                if len(trajectory) > 1:
                    dictlabel = matchwithlabel(trajectory,curlabellist)
                    traj_dict = {}
                    if dictlabel == "Unlabel": 
                        traj_dict["traj"] = trajectory 
                        traj_dict["label"] = "Unlabel" 
                        if len(trajectory)>=giveup_length:
                            unlabeldatalist.append(traj_dict)
                        
                        del trajectory 
                        
                    else:
                        if dictlabel[0]["start"] != 0:
                            
                            pretrajsegment,backtrajsegment,trajectory,dictlabel = cutunlabelsegment(trajectory,dictlabel)    
                            
                            unlabeltraj_dict = {}
                            unlabeltraj_dict["traj"] = pretrajsegment 
                            unlabeltraj_dict["label"] = "Unlabel"
                            if len(pretrajsegment) >= giveup_length:
                                unlabeldatalist.append(unlabeltraj_dict)

                            unlabeltraj_dict = {}
                            unlabeltraj_dict["traj"] = backtrajsegment 
                            unlabeltraj_dict["label"] = "Unlabel"
                            if len(backtrajsegment) >= giveup_length:
                                unlabeldatalist.append(unlabeltraj_dict)
                            
                            traj_dict["traj"] = trajectory 
                            traj_dict["label"] = dictlabel
                            if len(trajectory)>=giveup_length:
                                labeldatalist.append(traj_dict)
                            del traj_dict,trajectory
                        else:
                            
                            traj_dict["traj"] = trajectory 
                            traj_dict["label"] = dictlabel
                            if len(trajectory)>=giveup_length:
                                labeldatalist.append(traj_dict)
                            del traj_dict,trajectory
                        
        else:
            curtrajectorylist = []

            for trajectoryname in trajectorynamelist:
                inputpath = os.path.join(trajectorybasepath,trajectoryname)
                trajdatalist = loadtrajectory(inputpath)
                if len(trajdatalist)>1:
                    segmentlist = trajectorysegment(trajdatalist)
                    curtrajectorylist+=segmentlist 
            curtrajectorylist = mergetrajectorysegment(curtrajectorylist)
                         
            for trajectory in curtrajectorylist:
                if  len(trajectory)>1:        
                    traj_dict = {}
                    traj_dict["traj"] = trajectory 
                    traj_dict["label"] = "Unlabel"
                    if len(trajectory)>=giveup_length:            
                        unlabeldatalist.append(traj_dict)
                    del trajectory 
        del curtrajectorylist
                    
    joblib.dump(labeldatalist,labeldataoutputpath)
    del labeldatalist 
    joblib.dump(unlabeldatalist,unlabeldataoutputpath)
    del unlabeldatalist

def testfunction():
    inputpath = r'D:\Geolife Trajectories 1.3\Geolife Trajectories 1.3\Data\154\labels.txt'
    labellist = loadlabellist(inputpath)

    inputbasepath = r'D:\Geolife Trajectories 1.3\Geolife Trajectories 1.3\Data\154\Trajectory'
    filenamelist = os.listdir(inputbasepath)
    segmentlist = []
    for filename in filenamelist:
        inputpath = os.path.join(inputbasepath,filename)
        trajdatalist = loadtrajectory(inputpath)
        if len(trajdatalist)>0:
            trajsegmentlist = trajectorysegment(trajdatalist)
            segmentlist+=trajsegmentlist
         
    print(len(segmentlist))
    segmentlist = mergetrajectorysegment(segmentlist)
    print(len(segmentlist))
     
    for segment in segmentlist:
        trajdictlist = matchwithlabel(segment,labellist)
        if trajdictlist != "Unlabel":
            if trajdictlist[0]["start"] != 0:
                unlabeltrajsegment,datalist,trajdictlist = cutunlabelsegment(segment,trajdictlist)
        else:
            print(trajdictlist)
     

    
if __name__=='__main__':
    control()
    
        