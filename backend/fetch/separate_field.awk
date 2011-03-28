#!/usr/bin/awk -f
{
$0=$0",";
#while($0) {
        #print $0;
        match($0,/"[^"]*",|[^,]*,/);
        sf=f=substr($0,RSTART, RLENGTH);
        gsub(/"|,|utm_[^\&]*&|utm_[^\&]*$|src=*\&|src=*$/,"",f);
        if (match(f, /^http:/)){
                print f;
        }else{
                print "bad ", f;
        }
        #gsub(sf, "", $0);
#        }
}
