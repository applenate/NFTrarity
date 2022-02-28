# NFTrarity

1. getnft_info.py  从ipfs文件读NFT属性值，计算2种稀缺算法：
    1）常规：类似cowrarity ，将每个属性值计算分值，none也算分值
    2）NFTgo.io 算法：两两比较，计算每个NFT的平均差异值，然后再全集排序 （稀缺度算法见 NFTgo.io https://nftgo.medium.com/the-ultimate-guide-to-nftgos-new-rarity-model-3f2265dd0e23 ）

2.getprice.py  从os“请求”价格信息，根据UI文本标记，自动分类为多种价格，例如 buy now ，bid 等等

上述导出文件为Excel格式
