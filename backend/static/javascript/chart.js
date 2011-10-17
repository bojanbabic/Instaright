function drawVisualization(type, statsForDate, user) {
                                var options = {};
                                clearElement('visualization');
                                clearElement('statsHeader');
                                if (!statsForDate){
                                        var list = document.getElementsByClassName('menu_body_daily');
                                        try{
                                                statsForDate = list[0].getElementsByTagName('a')[0].innerHTML;
                                        } catch(e){
                                                try{
                                                        var y = new Date((new Date()).getTime() - 86400000);
                                                        statsForDate = y.getFullYear() +'-'+ y.getMonth() + '-'+ y.getDate();
                                                } catch(ee){
							alert(ee);
                                                } 
                                        }
                                        //statsForDate = "{{ dailyStats.0 }}";
                                        //statsForDate = "2010-08-24";
                                }
                                staticurl = '/visual?type=';
                                if (!type){
                                        typeString = 'dailyfeed';
                                        typeLabel="Daily stats for "+statsForDate;
                                        dataurl = staticurl + typeString + '&date=' + statsForDate;
                                }
                                else if (type == 1){
                                        typeString = 'weeklyfeed';
                                        typeLabel="Week stats for "+statsForDate;
                                        dataurl = staticurl + typeString + '&date=' + statsForDate;
                                }
                                else if (type == 2){
                                        typeString = 'dailyfeed';
                                        typeLabel="Daily stats for "+statsForDate;
                                        dataurl = staticurl + typeString + '&date=' + statsForDate;
                                } 
                                else if (type == 3){
                                        typeString = 'linkvolume';
                                        typeLabel="Daily Link Volume";
                                        dataurl = staticurl + typeString;
                                }
                                else if (type == 4){
                                        typeString = 'countryFeed';
                                        typeLabel="Most Instaright! Countries";
                                        dataurl = staticurl + typeString;
                                }
                                else if (type == 5){
                                        typeString = 'cityFeed';
                                        typeLabel="Most Instaright! Cities";
                                        dataurl = staticurl + typeString;
                                }
                                else if (type == 6){
                                        typeString = 'userfeed';
                                        typeLabel="Most Instaright! Users";
                                        if (user){
                                                dataurl = staticurl + typeString + '&user=' + user;
                                        } else {
                                                dataurl = staticurl + typeString + "&date=" + statsForDate;
                                        }
                                }
                                else {
                                        typeString = 'dailyfeed';
                                        typeLabel="Daily stats for "+statsForDate;
                                        dataurl = staticurl + typeString + '&date=' + statsForDate;
                                } 
                                setElementValue('statsHeader',typeLabel);
                                //typeString = 'weeklyfeed'
                                //alert(dataurl);

                                // 'bhg' is a horizontal grouped bar chart in the Google Chart API.
                                // The grouping is irrelevant here since there is only one numeric column.
                                options.cht = 'bhg'; 

                                // Draw labels in pink.
                                var color = 'ff3399';

                                // Google Chart API needs to know which column to draw the labels on.
                                // Here we have one labels column and one data column.
                                // The Chart API doesn't see the label column.  From its point of view,
                                // the data column is column 0.
                                var index = 0;

                                // -1 tells Google Chart API to draw a label on all bars.
                                var allbars = -1;

                                // 10 pixels font size for the labels.
                                var fontSize = 10;

                                // Priority is not so important here, but Google Chart API requires it.
                                var priority = 0;

                                var height = 450;
                                var weight = 500;
                                try{
                                        options.chm = [color, index, allbars, fontSize, priority].join(',');

                                        new google.visualization.Query(dataurl).send(
                                                        function(response){
                                                        //alert("response dat:"+response.getDataTable());
                                                        new google.visualization.ImageChart(document.getElementById('visualization')).draw(response.getDataTable(), options);  
                                                        });
                                        //document.getElementById('visualization1').innerHTML=dataurl;
                                } catch(e){
                                        alert(e);
                                }

                        }
