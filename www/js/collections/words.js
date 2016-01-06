var word_collection = Backbone.Collection.extend({ 
    model: word_class,

    url: function(){
      return "http://127.0.0.1:5000/wordlist?count=" + 
             settings.getSessionLength() + 
             "&maxlength=" + 
             settings.getMaxWord();
    },
    
    initialize : function (){
        console.log("initializing Collection");     
        this.listenTo(settings, "change", this.settingsChanged);
    },
    
    settingsChanged: function(){
      console.log("Collection settingsChanged");     
      this.fetch();
    },

});