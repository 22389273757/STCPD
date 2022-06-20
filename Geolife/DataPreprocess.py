import os
import time
import numpy as np
import pandas as pd
import datetime
from haversine import haversine
def loadOriginData(OriginFilePath):
    user_list = []
    for userid in os.listdir(OriginFilePath):
        user_traj_list = []
        for traj_filename in os.listdir(os.path.join(OriginFilePath,userid,"Trajectory")):
            traj_filename = os.path.join(OriginFilePath,userid,"Trajectory",traj_filename)
            record_list = []
            point_list = []
            for record in open(traj_filename,encoding="utf8"):
                record_list.append(record.replace("\n", "").split(","))
            record_list = record_list[6:]

            # 逐条处理源数据中的样本记录
            for data in record_list:
                lng = float(data[1])
                lat = float(data[0])
                daystr = np.array(data[-2].split("-"), dtype=int).tolist()
                timestr = np.array(data[-1].split(":"), dtype=int).tolist()
                datetimestr = daystr + timestr
                curdate = datetime.datetime(*datetimestr)

                #过滤样本中经纬度超出范围的记录
                lngmin,lngmax,latmin,latmax = 116.15,116.6,39.75,40.1
                if lng > lngmin and lng < lngmax and lat > latmin and lat < latmax:
                    point_list.append([lat, lng, curdate])

                #根据时间间隔或距离间隔将坐标列表分割成多条轨迹
                distance_threshold,time_threshold = 2000,1200   #两点间隔2km,20min以内的轨迹视作连续轨迹点
                if len(point_list)>1:
                    break_point = [0]
                    for index in range(len(point_list) - 1):
                        curpoint = point_list[index]
                        nextpoint = point_list[index + 1]
                        distance_interval = haversine(curpoint[:2], nextpoint[:2])
                        time_interval = np.fabs((nextpoint[2] - curpoint[2]).total_seconds())
                        if distance_interval > distance_threshold or time_interval > time_threshold:
                            break_point.append(index + 1)
                    break_point.append(len(point_list))
                    traj_list = []
                    for index in range(len(break_point) - 1):
                        if (break_point[index+1] - break_point[index]) > 2:
                            traj_list.append(point_list[break_point[index]:point_list[index+1]])

            #处理两个文件连接处的轨迹拼接问题
            distance_threshold, time_threshold = 2000, 1200
            if len(user_traj_list)>0 and np.fabs((traj_list[0][0][-1]-user_traj_list[-1][-1][-1]).total_seconds())<time_threshold:
                user_traj_list[-1]+=traj_list[0]
                user_traj_list.extend(traj_list[1:])
            else:
                user_traj_list.extend(traj_list)

        #分别处理带标签数据与不带标签数据
        if os.path.exists(os.path.join(OriginFilePath,userid,"labels.txt")):

            pass
        for user_traj in user_traj_list:
            if len(user_traj)>1:







if __name__ == "__main__":
    origin_data = loadOriginData("../OriginData")
