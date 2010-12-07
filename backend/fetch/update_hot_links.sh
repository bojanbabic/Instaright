HOT_LINKS=$1
if [ $# != 1 ];then
        echo "need to specify hot links file"
        exit
fi
if [ ! -f "$HOT_LINKS" ];then
        echo "need to specify proper file"
        exit
fi

head -1000 "$HOT_LINKS" | awk '{print "count="$1"&url="$2}' | while read line;do  curl -d "$line"  http://localhost:8080/link/add ;done 

