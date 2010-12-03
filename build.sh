cd $HOME/d/work/_ff_extensions/instaright/
version=`grep "em:version" install.rdf  | sed -E  "s/.*>(.*)<.*/\\1/" `
cat content/instaright/about.xul | sed -e "s/value=\"ver\.\ .*\"/value=\"ver\.\ $version\"/"  > content/instaright/about.xul.new
mv content/instaright/about.xul.new content/instaright/about.xul
zip -vr chrome/instaright.zip content/ skin/ locale/ -x "*.svn*"
mv chrome/instaright.zip chrome/instaright.jar
cat modules/AddonManager.jsm | sed -E "s/VERSION=.*/VERSION=\"$version\";/" > modules/AddonManager.jsm.new
mv modules/AddonManager.jsm.new modules/AddonManager.jsm
zip -vr instaright.zip chrome/ icon.png install.js  install.rdf chrome.manifest defaults/ modules/  -x "*.svn*"
mv instaright.zip instaright.xpi
