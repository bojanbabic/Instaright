function check_and_send_jid(){
        jid= $("#invite_jid").val();     
        if (jid.indexOf("@") == -1 || jid.indexOf(" ") != -1){
                $("#jid_result").html("<b>not valid jabber address</b>");
                $("#jid_result").show();
        }
        else{
                send_invite();
                $("#jid_result").html("<b>Message sent. you will receive IM from instaright@appspot.com</b>");
                $("#jid_result").show();
        }
        $("#jid_result").delay(2000).fadeOut('slow');
        $("#invite_jid").val('');     
}
function send_invite(){
        try{
                $.post("/send_invite", $("#invite_jid").val());
        } catch(e){
                alert('e:'+e);
        }

}
