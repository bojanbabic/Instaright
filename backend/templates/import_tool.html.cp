<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <script type="text/javascript">var tinyMCE,_sf_startpt=(new Date()).getTime();</script>
        <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.4/jquery.min.js"></script>
        <script src="/static/javascript/jquery.form.js"></script>
        <script src="/static/javascript/validate.js"></script>
        <script src="/static/javascript/tooltip.js"></script>
        <script type="text/javascript" src="http://github.com/malsup/form/raw/master/jquery.form.js?v2.44"></script>

        <script src="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8/jquery-ui.min.js"></script>

        
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <meta name="viewport" content="width = 900"/>
        <meta name="keywords" content="export delicious to instapaper, how to export delicious bookmarks to instapaper, instapaper import delicious, delicious to instapaper, import delicious bookmarks, instapaper delicious"/>
        
        <title>Import Delicious Bookmarks</title>
        
                    <!--link rel="stylesheet" type="text/css"href="http://assets.tumblr.com/stylesheets/compressed/account_form.css?410"/-->
        <link rel="stylesheet" type="text/css" href="/css/landing_form.css"/>
        <link rel="stylesheet" type="text/css" href="/css/style.css"/>
        <link rel="stylesheet" type="text/css" href="/css/tooltip.css"/>
            
      </head>
    <body>
        
        <script type="text/javascript" charset="utf-8">
                $(document).ready(function(){
		        $('#iuser').focus();
                        $('#import_form').validate();
                        $('#import_form').ajaxForm({ 
                                        target: '#response', 
 
                                        // success identifies the function to invoke when the server response 
                                        // has been received; here we apply a fade-in effect to the new content 
                                        success: function() { 
                                                $('#response').fadeIn('slow'); 
                                        } 
                                }); 
                });
        </script>
        <div id="container">
            <div id="header_container">
                <div id="header">
                </div>
            </div>
           <div id="content">
                


<!--[if IE 6]>
    <style type="text/css">
        #content  #form #form_inner #account_form .text_field, 
        #content #form #form_inner,
        #content #form {
            background-image: none;
        }
        
        #footer {
            margin-top: -100px
        }
    </style>
<![endif]-->


<div id="inset">
    <div id="inset_shimmer">
        <div class="slogan">Import Delicious public bookmarks into Instapaper</div>
    </div>
</div>

<div id="form">
    <div id="form_inner">
        <form action="/tools/import/delicious" method="post" id="import_form">
            
           <div style="display: block;"> 
            {% if not token %}
                <!--label for="duser">Delicious Account <span class="toolTip" title="Use your yahoo user name. ie. if your yahoo mail is instaright@yahoo.com then your account is instaright">&nbsp;</span></label>
                <div style="margin-bottom: 20px;"><input type="text" name="duser" id="duser" class="required text_field" value=""/></div-->
                <label><a href="{{ yahoo_login_url }}">Login with Yahoo Account</a></label>
            {% else %}
                <label>Logged in</label>
                <input type="hidden" name="token" id="token" value="{{ token }}"/>
                <input type="hidden" name="oauth_token_secret" id="oauth_token_secret" value="{{ oauth_token_secret }}"/>
            {% endif %}
            <label for="iuser">Instapaper Account</label>
            <div style="margin-bottom: 20px;"><input type="text" name="iuser" id="iuser" class="required text_field" value=""/></div>
            <label for="ipass">Password <span class="toolTip" title="Only if you have set your instapaper password">&nbsp;</span></label>
            <div style="margin-bottom: 30px;"><input type="password" name="ipass" class="text_field"/></div>
            <div>
                <input type="submit" value="Import" class="big_button" />
            </div>
          </div>
       </form>
    </div>
    <div id="big_button1">
            more about: <a href="http://instaright.posterous.com/delicious-is-dead-long-live-instapaper" title="How to import Delicious bookmarks to Instapaper">How to export Delicious bookmarks to Instapaper →</a>
    </div>
 </div>
<div id="response"></div>
</div>

            
            <div id="footer-container">
                <div style="position: relative; text-align: center; color: rgb(0, 0, 204); font-size: small;">
                        <p><a href="mailto:gbabun@gmail.com" title="Contact Instaright developer">contact</a> | <a href="http://twitter.com/instaright" title="instaright on twitter">twitter</a> | <a href="http://instaright.tumblr.com" title="instaright blog">blog</a></p>
                </div>
            </div>
        </div>
<!-- apture bar -->
<script id="aptureScript">
(function (){var a=document.createElement("script");a.defer="true";a.src="http://www.apture.com/js/apture.js?siteToken=B6cWD6D";document.getElementsByTagName("head")[0].appendChild(a);})();
</script>
<!-- end apture bar -->
<!-- GETSATISFACTION -->
<script type="text/javascript" charset="utf-8">
        var is_ssl = ("https:" == document.location.protocol);
        var asset_host = is_ssl ? "https://s3.amazonaws.com/getsatisfaction.com/" : "http://s3.amazonaws.com/getsatisfaction.com/";
        document.write(unescape("%3Cscript src='" + asset_host + "javascripts/feedback-v2.js' type='text/javascript'%3E%3C/script%3E"));
        </script>

        <script type="text/javascript" charset="utf-8">
                var feedback_widget_options = {};

feedback_widget_options.display = "overlay";  
feedback_widget_options.company = "instaright";
feedback_widget_options.placement = "left";
feedback_widget_options.color = "#222";
feedback_widget_options.style = "idea";
var feedback_widget = new GSFN.feedback_widget(feedback_widget_options);
</script>
    </body>
</html>

