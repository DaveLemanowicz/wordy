var word_collection = Backbone.Collection.extend({ 
    model: word_class,
    url: "http://127.0.0.1:5000/wordlist?count=20&maxlength=4",
    //url: "http://192.168.1.185:5000/wordlist?count=20&maxlength=4",

});