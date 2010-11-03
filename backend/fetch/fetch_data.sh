#!/bin/bash
OUTPUT_DIR=$1
if [ ! -d $OUTPUT_DIR ];then
        echo "provide proper dir"
        exit
fi
curl -s http://instaright.appspot.com/user/stats/top/1?format=txt |  
while read line;
        do echo "processing $line...."; 
        if [ -e "$OUTPUT_DIR/$line.dat" ];then
                echo "user $line already processed"
                continue
        fi
        response=`curl -s -d "username=$line&password=" https://www.instapaper.com/api/authenticate 2> /tmp/err`; 
        if [ "$response" = "200" ];then
                        curl -s -d "username=$line" http://www.instapaper.com/user/login -c /tmp/$line"_cookie.txt" > /tmp/out
        else
                        echo "no access :$response; skipping"
                        continue
        fi
        form_key=`curl -s http://instaright.appspot.com/user/$line/form_key`
        if [ ! "$form_key" ];then
                        form_key=`curl -s -L -H "User-Agent:Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10 (.NET CLR 3.5.30729);" -H "Proxy-Connection: keep-alive" http://www.instapaper.com/u -b /tmp/$line"_cookie.txt"  | grep -o "form_key.*value=\"[^\"]*" | sed  -E 's/.*value=\"(.*)/\1/'  | uniq`
                        echo "new form_key $form_key"
                        curl -s -d "" http://instaright.appspot.com/user/$line/$form_key
        fi
        #form_key = `curl http://localhost:8080/user/$line/form_key`
        curl -s -L -H "User-Agent:Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10 (.NET CLR 3.5.30729);" -H "Connection:close;" -H "Content-Type: application/x-www-form-urlencoded;" -d "form_key=$form_key"  http://www.instapaper.com/export/csv -b /tmp/$line"_cookie.txt" > "$OUTPUT_DIR/$line.dat"
        sleep $[($RANDOM % 5) +1 ]
        echo "done"
        echo "" 
done 
