@0xf0ef0a5c0aad9f4a; 


struct Schema {
  supported @0: List(HWCombo); # List of known hw combinations
  botToken @1: Text; # token of the telegram bot
  chatId @2: Text; # id of the telegram groupchat
}

struct HWCombo {
  hddCount @0: UInt16; # expected number of hdds
  ssdCount @1: UInt16; # expected number of ssds
  ram @2: UInt64; # expected amount of ram (in mibi bytes - MiB)
  cpu @3: Text; # model name of expected cpu
  name @4: Text; # name of this hw combo
}