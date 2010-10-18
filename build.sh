cd $HOME/d/work/_ff_extensions/instaright/
zip -vr chrome/instaright.zip content/ skin/  -x "*.svn*"
mv chrome/instaright.zip chrome/instaright.jar
version=`grep "em:version" install.rdf  | sed -E  "s/.*>(.*)<.*/\\1/" `
cat modules/AddonManager.jsm | sed -E "s/VERSION=.*/VERSION=\"$version\";/" > modules/AddonManager.jsm.new
mv modules/AddonManager.jsm.new modules/AddonManager.jsm
zip -vr instaright.zip chrome/ icon.png install.js  install.rdf chrome.manifest defaults/ modules/  -x "*.svn*"
mv instaright.zip instaright.xpi
