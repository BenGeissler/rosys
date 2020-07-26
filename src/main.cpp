#include <map>
#include "esp_system.h"
#include "nvs_flash.h"

#include "storage.h"
#include "modules/Module.h"
#include "modules/Esp.h"
#include "modules/Configure.h"
#include "utils/Serial.h"
#include "utils/timing.h"
#include "utils/strings.h"

std::map<std::string, Module *> modules;

Serial *serial;

void handleMsg(std::string msg)
{
    std::string module_name = cut_first_word(msg);
    if (modules.count(module_name))
        modules[module_name]->handleMsg(msg);
    else if (module_name == "pw")
        handleMsg(std::string("dm pw ") + msg);
    else
        printf("Unknown module name: %s\n", module_name.c_str());
}

void setup()
{
    serial = new Serial(115200);
    delay(500);

    storage::init();

    modules["esp"] = new Esp();
    modules["configure"] = new Configure(modules, handleMsg);

    for (auto const &item : modules)
        item.second->setup();
}

void loop()
{
    while (true)
    {
        std::string line = serial->readStringUntil('\n');
        if (line.empty())
            break;
        handleMsg(line);
    }

    for (auto const &item : modules)
        item.second->loop();

    delay(10);
}

extern "C"
{
    void app_main();
}
void app_main()
{
    setup();

    while (true)
        loop();
}
