#coding:UTF-8
import os
from requests_html import HTMLSession
import json
import xlsxwriter as xw
import time
import datetime
'''
IPFS browser:
http://cloudflare-ipfs.com/ipfs/
https://ipfs.io/ipfs/
https://ikzttp.mypinata.cloud/ipfs/
'''

uri = "https://ikzttp.mypinata.cloud/ipfs/QmQFkLSQysj94s5GvTHPyzTxrawwtjgiiYS2TBLgrvw8CW/"
#填写token个数,冷兔是7502,azuki 10k,QmQFkLSQysj94s5GvTHPyzTxrawwtjgiiYS2TBLgrvw8CW
num_tokens = 10000
fileName = 'nfts_azuki.xlsx' #导出文件名
session = HTMLSession()
seprate ='__________________________________________________________________________\n'

data = {} #全部nft信息

'''
data是NFTs属性信息字典，数据格式
{
	tokenid_1:
	{	
		"name":value,
		"image":value,
		"has_attributes":1  #0，无属性不参与排名；1，有属性参与排名
		"attributes":
			{
				type_1:value, #属性信息
				type_2:value,
			}
		"attributes_none":  #二次填充，没有属性值的属性类型
			[
			type_3,
			type_4,
			type_5	
			]
		"trait_count":value, #int
		"rarity_score_nftgo":value, #nftgo的稀缺算法
		"rarity_rank_nftgo":value, #稀缺排名
		"rarity_score_cow":value, #rarity的稀缺算法
		"rarity_rank_cow":value, 
	},

	tokenid_2:
	{
		"name":value,
		"image":value,
		"has_attributes":0 #为0，无属性不参与排名
		"attributes":{}
		"attributes_none": []
		"trait_count":0, #int
		"rarity_score_nftgo":none, 
		"rarity_rank_nftgo":none, 
		"rarity_score_cow":none,
		"rarity_rank_cow":none,
	},
	...
	
}
'''




'''


data_traits 属性库，collection的属性统计表（int）：
{
	"traits_count":  #getNFT_info 时已录入
		{
		1:value,
		2:value,
		3:value,
		...
		},
	"traits_details": #getNFT_info 时已录入
		{"body":
			{
				"Blue ghost":value,  #int属性值统计个数
				"Yellow ghost":value,
				"<none>":value, #初始0，需要二次累加
				...
			},
		"head":
			{
				"Halo":value,
				"<none>":value,
				...
			},
		"Clothes":
			{
				...
			}
		...
		},
	"traits_score": #需要三次计算
		{
		"traits_count":
			{
				1 : score_value,   #  属性值:分值
				2 : score_value,
				3 : score_value,

			}
		"body":
			{
				"Blue ghost":value,  #属性分值
				"Yellow ghost":value,
				"<none>":value,
				...
			}
		...
}
'''

#初始化属性库
data_traits = {
		"traits_count":{},
		"traits_details":{},
		"traits_score":{}
	}



#抓属性
def getNFT_info(tokenid,uri):

	infos = {} #属性详情

	#定义URI格式，有的需要追加".json"
	url = uri+str(tokenid)
	
	req_text = session.get(url).text
	req = json.loads(req_text)
	# print(url)
	# print(req)
	infos["name"] = req["name"]
	infos["image"] = req["image"]
	infos["attributes"] = {}  #初始化属性信息
	#print(tokenid,type(infos["attributes"]))

	#有属性字段
	if "attributes" in req.keys():

		#属性字典有dict的（有值的）
		if type(req["attributes"]) == list :
			infos["has_attributes"] = 1 #1有属性，参与排名
			attributes = req["attributes"]
			trait_count = 0
			for item in attributes:
				trait_type = item["trait_type"]
				value = item["value"]
				infos["attributes"][trait_type] = value

				#创建type，并"<none>"初始化为0
				if trait_type not in data_traits["traits_details"].keys():
					data_traits["traits_details"][trait_type] = {"<none>":0}
				if value not in data_traits["traits_details"][trait_type].keys(): #新增属性值统计
					data_traits["traits_details"][trait_type][value] = 1
				else :
					data_traits["traits_details"][trait_type][value] += 1

				trait_count += 1 #int统计当前NFT总共有多少属性
			infos["trait_count"] = trait_count
			infos["attributes_none"] = []  #初始化无属性值的类型
			#统计属性库
			if trait_count not in data_traits["traits_count"].keys() :
				data_traits["traits_count"][trait_count] = 1
			else :
				data_traits["traits_count"][trait_count] += 100		

	#没有属性的，包括没有属性字段的
	else:
		infos["has_attributes"] = 0 #0无属性，不参与排名
		infos["attributes"] = {}
		infos["attributes_none"]: []
		infos["trait_count"] = 0

	infos["rarity_score_nftgo"] = None
	infos["rarity_rank_nftgo"] = None
	infos["rarity_score_cow"] = None
	infos["rarity_rank_cow"] = None
	return infos

#稀缺度算法见 NFTgo.io https://nftgo.medium.com/the-ultimate-guide-to-nftgos-new-rarity-model-3f2265dd0e23 
#计算两个token差异值
def get_JD(tokenId_1,tokenId_2,data):
	info1 = data[tokenId_1]["attributes"]
	info2 = data[tokenId_2]["attributes"]
	c1 = set(info1.items())
	c2 = set(info2.items())
	result = 1 - len(c1 & c2) / len(c1 | c2)
	return result

# NFTGO.io的稀缺度算法，计算两两NFT的属性差值，计算差异度，稀缺值，稀缺排名，填充回原始data数据
def get_JDs(data):
	print (time.strftime("-  开始计算差异值  %Y-%m-%d %H:%M:%S", time.localtime()) )
	data_JDs = {}  #字典，当前token对其他所有token差异值的平均数
	data_JDs_list = [] #列表化，方便找到最大最小值
	n = len(data)
	for i in range(n):
		temp = 0

		if data[i]["has_attributes"] == 1 :  #如果有属性
			
			for j in range(n):

				if data[j]["has_attributes"] == 1: #如果有属性
					if i != j :
						value = get_JD(i,j,data)
						temp += value
			data_JDs[i] = temp/(n-1)
			print("(NFTgo.io 1/2) >  ID "+str(i)+" 平均差异值："+str(temp/(n-1)))
			data_JDs_list.append(temp/(n-1))

	print (time.strftime("-  开始计算稀缺度排名  %Y-%m-%d %H:%M:%S", time.localtime()) )
	data_JDs_list.sort(reverse=True)  #从大到小排序，值越大，越稀缺

	lenth_data_JDs_list = len(data_JDs_list)
	value_min = data_JDs_list[lenth_data_JDs_list-1]
	value_max = data_JDs_list[0]
	value_devide = value_max - value_min
	for item in data_JDs.keys():
		value_item = data_JDs[item]
		rarity_score = ((value_item - value_min)/value_devide) * 100
		rarity_rank = data_JDs_list.index(value_item)+1 #rank排序。找出排序列表的位置，排名需要+1
		print("(NFTgo.io 2/2) >  ID "+str(item)+" 稀缺度："+str(rarity_score)+"   排名： "+str(rarity_rank))
		data[item]["rarity_score_nftgo"] = rarity_score
		data[item]["rarity_rank_nftgo"] = rarity_rank
	return data

#https://raritycow.io/的算法，计算每个属性的分值，即使为none空，也计算在内

#填充data信息，填充没有值的属性，同时在data_traits属性库里累计个数完善属性库
def count_type_none(data,data_traits):
	for i in data.keys():
		if data[i]["has_attributes"] == 1:
			info = data[i]
			info_types = info["attributes"].keys()
			data_traits_types = data_traits["traits_details"].keys()
			for type_name in data_traits_types :  #属性库里的类型名，与当前NFT的属性类型名，依次匹配，如果没有找到，则none +1
				if type_name not in info_types :
					data[i]["attributes_none"].append(type_name) #填充进data，列表
					data_traits["traits_details"][type_name]["<none>"] += 1 #统计进属性库
	return

'''
算法：NFT总个数7502*特征值总个数339/特征分类个数8 = 特征分类总积分，
然后每行特征值*count个数 = 每行积分恒定，
即，每行积分恒定 = 特征分类总积分/特征值个数 （比如说除以52，即为6113.41）
'''
# 统计特征值个数
def count_traits(data_traits):
	num = 0
	num += len(data_traits["traits_count"].keys())
	types_values = list(data_traits["traits_details"].values())
	for item in types_values:
		if item["<none>"] == 0 :
			num += (len(item.keys()) - 1 )
		else:
			num += len(item.keys())
	print("num :",num)
	return num

#更新特征值分值（cow算法）
def update_traits_scores(num_has_attributes,data_traits):
	num = count_traits(data_traits) #特征值总个数
	num_column = len(data_traits["traits_details"].keys()) + 1  #特征分类数，+1是因为把属性个数也算新增的属性，看一下summary sheet的表格列
	X = num_has_attributes * num / num_column  #单列总和，即，有属性的有效NFT总个数7502*特征值总个数339/特征分类个数8

	#先计算 traits_count 的分值
	Y = 0 #初始化单行恒定乘积值
	Y = X / len(data_traits["traits_count"].keys())
	data_traits["traits_score"]["traits_count"] = {}  #新建traits_count 子key
	for item in data_traits["traits_count"].keys():
		key_score = Y / data_traits["traits_count"][item]
		data_traits["traits_score"]["traits_count"][item] = key_score

	
	#然后计算属性分值
	for item in data_traits["traits_details"].keys() :
		Y = 0 #初始化单行恒定乘积值
		data_traits["traits_score"][item] = {}  #新建traits_details 子key
		if data_traits["traits_details"][item]["<none>"] == 0 :
			Y = X / ( len(data_traits["traits_details"][item].keys()) - 1 )
		else :
			Y = X / len(data_traits["traits_details"][item].keys())
		#填充分值
		for key in data_traits["traits_details"][item].keys() :
			data_traits["traits_score"][item][key] = 0  #新建子key
			if data_traits["traits_details"][item][key] != 0 :
				data_traits["traits_score"][item][key] = Y / data_traits["traits_details"][item][key]
	print("✔   update_traits_scores 各属性分值如下：")
	print(seprate)
	print(data_traits["traits_score"])
	print(seprate)

	return data_traits


#计算cow算法分值和排名
def update_data_cowscore(data,data_traits):
	cow_score_list = []  #缓存一下cow分值
	for tokenid in data.keys():
		if data[tokenid]["has_attributes"] == 1:
			rarity_score_cow = 0
			trait_num = 0
			trait_num = len(data[tokenid]["attributes"].keys())

			#先把属性类别数量这个分值加上
			rarity_score_cow += data_traits["traits_score"]["traits_count"][trait_num]

			#然后再加各个属性分值
			#(1/2) 有值的属性分值
			for type_name in data[tokenid]["attributes"].keys():  #取属性类别
				value = data[tokenid]["attributes"][type_name]
				rarity_score_cow += data_traits["traits_score"][type_name][value]
			#(2/2)为"<none>"的属性分值
			for type_name in data[tokenid]["attributes_none"]: 
				rarity_score_cow += data_traits["traits_score"][type_name]["<none>"]
				
			data[tokenid]["rarity_score_cow"] = rarity_score_cow

			cow_score_list.append(rarity_score_cow) #cow分值列表，排序用

			print("cow(1/2)>  Id: ",tokenid," cow分值：",rarity_score_cow)

	print("✔   cow分值计算完毕")

	#cow分值排名
	cow_score_list.sort(reverse=True)  #从大到小排序，值越大，越稀缺

	for tokenid in data.keys():
		if data[tokenid]["has_attributes"] == 1:
			rarity_score_cow = data[tokenid]["rarity_score_cow"]
			rarity_rank_cow = cow_score_list.index(rarity_score_cow)+1
			data[tokenid]["rarity_rank_cow"] = rarity_rank_cow
			print("cow(2/2)>  Id: %d  cow分值： %.2f   排名：  %d"%(tokenid,rarity_score_cow,rarity_rank_cow))


#写Excel
def xw_toExcel(data,fileName):
	print (time.strftime("-  开始写Excel  %Y-%m-%d %H:%M:%S", time.localtime())) 
	workbook = xw.Workbook(fileName)
	worksheet1 = workbook.add_worksheet("Sheet1")
	worksheet1.activate()
	type_names = data_traits["traits_details"].keys()
	title = ['ID','img', 'name', 'NFTIO_score','NFTIO_rank', 'cow_score','cow_rank'] + list(type_names) #从A1单元格开始写表头

	worksheet1.write_row('A1',title) #A1开始写表头
	i = 2 #第二行开始写数据
	lenth = str(len(data))
	for j in range(len(data)):  #全量列出来，即使没有属性，不参与排名的
		info = data[j]
		insertData =[]  #初始化即将插入的列表
		id_name = "#"+str(j)
		img = info["image"]
		name = info["name"]
		NFTIO_score = info["rarity_score_nftgo"]
		NFTIO_rank = info["rarity_rank_nftgo"]
		cow_score = info["rarity_score_cow"]
		cow_rank = info["rarity_rank_cow"]
		insertData = [id_name,img,name,NFTIO_score,NFTIO_rank,cow_score,cow_rank]

		#下面查询属性
		#对于有属性的token
		if data[j]["has_attributes"] == 1:
			info_attributes = info["attributes"]
			info_attributes_dict = info_attributes.keys()
			for item in list(type_names):  #全量属性字典
				if item in info_attributes_dict:
					insertData += [info_attributes[item]]
					#print(insertData)
				else :
					insertData += ["<none>"]  #逐列查询值，为空则写<none>
					#print(insertData)
		#对于无属性的token，不追加属性内容

		row = 'A' + str(i)
		worksheet1.write_row(row,insertData)

		#图片地址，需要根据具体的图片路径修改
		link_url = img.split("//")[1]  #取ipfs图片路径的后缀
		link = "https://ipfs.io/ipfs/"+link_url  
		worksheet1.write_url(j+1,1,link,string=link_url)  #修改为图片实际url路径
		print("-  已写入个数:  "+str(j+1)+" / "+lenth)
		i += 1
	
	print (time.strftime("✔   已保存： Sheet1   %Y-%m-%d %H:%M:%S", time.localtime()) )

	#写第二个表格，全局属性统计表
	worksheet2 = workbook.add_worksheet("Summary")
	worksheet2.activate()

	title2 = ["属性个数统计","数量"]
	for item in type_names:
		title2 += [item,"count"]
	worksheet2.write_row('A1',title2) #A1开始写表头
	
	#左侧是属性个数统计列表
	traits_num = list(data_traits["traits_count"].keys())
	traits_count = list(data_traits["traits_count"].values())
	worksheet2.write_column("A2",traits_num)
	worksheet2.write_column("B2",traits_count)
	#print(list(type_names))

	#右侧是属性详情统计，第三列开始写
	for j in range(2,len(title2)):
		insertData = []
		key = list(type_names)[(j-2)//2]
		for item in data_traits["traits_details"]:
			if j % 2 == 0:
				insertData = list(data_traits["traits_details"][key].keys())

			else:
				insertData = list(data_traits["traits_details"][key].values())
			#写列
			worksheet2.write_column(1,j,insertData)
		j += 1

	workbook.close()
	print (time.strftime("✔   已保存： Sheet2   %Y-%m-%d %H:%M:%S", time.localtime()) )
	print('✔   已保存： %s'%fileName)




print(seprate)
time_start = time.time() #开始时间
print (time.strftime("  %Y-%m-%d %H:%M:%S",time.localtime()) )
print("开始读取url    "+uri)
print("token总数：   %d"%num_tokens)
print("将保存为文件：  "+fileName)


#统计有属性的token个数
num_has_attributes = 0 


for i in range (num_tokens):

	data[i] = getNFT_info(i,uri)
	if data[i]["has_attributes"] == 1:
		num_has_attributes += 1
	print(">  "+str(i))
	# time.sleep(0.3)
	if (i >0 ) & (i % 500 == 0):
		jindu = (( i + 1 )/num_tokens)  #float 显示进度
		time_now = time.time() 
		time_used = time_now - time_start
		time_remain = ( time_used / jindu ) * (1 - jindu) + 5
		print("-  sleep 5 seconds   预计还需 ",datetime.timedelta(seconds=int(time_remain)),"   已用时 ",datetime.timedelta(seconds=int(time_used)))
		time.sleep(5)

print(seprate)

#统计属性类型为空的个数
count_type_none(data,data_traits) 

#更新cow算法的特征值分值，仅计算有属性的有效NFT
update_traits_scores(num_has_attributes,data_traits)

#插入cow算法分值
update_data_cowscore(data,data_traits)

#data里插入nftgo.io的稀缺值
get_JDs(data)
print(seprate)

#写Excel
xw_toExcel(data,fileName)
time_end = time.time() #结束时间
deltatime = int(time_end - time_start)
print("    总耗时： ",datetime.timedelta(seconds=deltatime))
print(seprate)



