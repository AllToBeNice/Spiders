echo "疫情分布爬虫运行中"
Get-Date
while(1){
    # 当分钟为00或30时，执行Python脚本，并打开图片网页
    # 当时间为000100，即过零点1分时，退出程序
    if( ($((Get-Date).Minute) -eq 00) -and ($((Get-Date).Minute) -eq 30 )){
    python37 F:\Python\Project\新型冠状病毒疫情分布图\新型冠状病毒疫情分布图.py
    Start-Process -Wait -FilePath chrome F:\Python\Project\新型冠状病毒疫情分布图\疫情分布图.html
    # F:\Python\Project\新型冠状病毒疫情分布图\疫情分布图.html
    }elseif($(Get-Date -Format 'hhmmss') -eq 000100){
    exit
    }else{
    if($(Get-Date -Format 'hhmmss') % 4 -eq 0){ -join("运行中", "--")}
    }
    ## 等待3 min
    # sleep $(3 * 60)
    ##-join("运行中", "--")
}