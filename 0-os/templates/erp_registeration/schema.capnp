@0xcdc53cba610a4800; 


struct Schema {
  url @0: Text; # url of the Odoo server
  db @1: Text; # name of the Odoo database
  username @2: Text; # credentials for the Odoo server
  password @3: Text;
  productId @4: UInt32; # id of the product to couple the node to in Odoo
  botToken @5: Text; # token of the telegram bot
  chatId @6: Text; # id of the telegram groupchat

}
