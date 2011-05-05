RC=false
if [ $# == 1 -a "$1" == "release" ];then
	RC=true
fi
version=`grep "em:version" install.rdf  | sed -E  "s/.*>(.*)<.*/\\1/" `
cat content/instaright/about.xul | sed -e "s/value=\"ver\.\ .*\"/value=\"ver\.\ $version\"/"  > content/instaright/about.xul.new
mv content/instaright/about.xul.new content/instaright/about.xul
rm chrome/instaright.jar
zip -vr chrome/instaright.zip content/ skin/ locale/ -x "*.svn*"
mv chrome/instaright.zip chrome/instaright.jar
zip -vr instaright.zip chrome/ install.js  install.rdf chrome.manifest defaults/ privacy_policy.txt  -x "*.svn*" -x "*Originals*"
mv instaright.zip instaright.xpi
cp instaright.xpi backend/tools/addon
