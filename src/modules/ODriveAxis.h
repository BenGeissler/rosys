#pragma once

#include <string>
#include <math.h>

#include "Module.h"
#include "../ports/Port.h"
#include "../utils/strings.h"
#include "../modules/Can.h"
#include "../modules/Button.h"
#include "../utils/checksum.h"

class ODriveAxis : public Module
{
private:
    float minPos = -INFINITY;
    float maxPos = INFINITY;
    float tolerance = 0.005;
    float moveSpeed = INFINITY;
    float homeSpeed = -0.1;
    float mPerTick = 0.01;

    Can *can;
    uint16_t can_id;
    Button *home_switch;

    float position = 0.0;
    float tickOffset = 0.0;
    uint8_t error = 0;

    struct odriveState_t {
        uint8_t state;
        uint8_t controlMode;
        uint8_t inputMode;
    } odriveState;

    enum State
    {
        STOP = 0,
        MOVE = 1,
        HOME = 2,
        HOMING = 3,
    };

public:
    ODriveAxis(std::string name, Button *home_switch, Can *can, std::string parameters) : Module(name)
    {
        this->can = can;
        this->can_id = std::stoi(parameters, nullptr, 16);
        this->home_switch = home_switch;
        this->can->subscribe(this->can_id + 0x001, this);
        this->can->subscribe(this->can_id + 0x009, this);
    }

    void loop()
    {
        this->can->send(this->can_id + 0x009, 0, 0, 0, 0, 0, 0, 0, 0, true);

        if (this->state == HOMING and this->is_home_active())
        {
            this->stop();
        }

        Module::loop();
    }

    std::string getOutput()
    {
        char buffer[256];
        std::sprintf(buffer, "%d %d %.3f", this->state, this->error, this->position);
        return buffer;
    }

    void handleMsg(std::string command, std::string parameters)
    {
        if (command == "move")
        {
            float target = atof(cut_first_word(parameters, ',').c_str());
            float speed = this->moveSpeed;
            if (not parameters.empty()) {
                speed = atof(parameters.c_str());
            }
            this->move(target, speed);
        }
        else if (command == "dmove")
        {
            float target = atof(cut_first_word(parameters, ',').c_str()) + this->position;
            float speed = this->moveSpeed;
            if (not parameters.empty()) {
                speed = atof(parameters.c_str());
            }
            this->move(target, speed);
        }
        else if (command == "speed")
        {
            this->speed(atof(parameters.c_str()));
        }
        else if (command == "torque")
        {
            this->torque(atof(parameters.c_str()));
        }
        else if (command == "home")
        {
            this->home();
        }
        else if (command == "stop")
        {
            this->stop();
        }
        else if (command == "reboot")
        {
            this->can->send(this->can_id + 0x016, 0, 0, 0, 0, 0, 0, 0, 0);
        }
        else if (command == "clearError")
        {
            this->can->send(this->can_id + 0x018, 0, 0, 0, 0, 0, 0, 0, 0);
        }
        else
        {
            Module::handleMsg(command, parameters);
        }
    }

    void handleCanMsg(uint16_t can_id, uint8_t data[8])
    {
        if (can_id == this->can_id + 0x001)
        {
            this->error = data[0];
        }
        if (can_id == this->can_id + 0x009)
        {
            float tick;
            std::memcpy(&tick, data, 4);
            if (this->is_home_active())
            {
                this->tickOffset = tick;
            }
            this->position = (tick - this->tickOffset) * this->mPerTick;
        }
    }

    void set(std::string key, std::string value)
    {
        if (key == "minPos")
        {
            minPos = atof(value.c_str());
        }
        else if (key == "maxPos")
        {
            maxPos = atof(value.c_str());
        }
        else if (key == "tolerance")
        {
            tolerance = atof(value.c_str());
        }
        else if (key == "moveSpeed")
        {
            moveSpeed = atof(value.c_str());
        }
        else if (key == "homeSpeed")
        {
            homeSpeed = atof(value.c_str());
        }
        else if (key == "mPerTick")
        {
            mPerTick = atof(value.c_str());
        }
        else
        {
            Module::set(key, value);
        }
    }

    void move(float target, float speed)
    {
        this->setMode(8, 3, 1); // AXIS_STATE_CLOSED_LOOP_CONTROL, CONTROL_MODE_POSITION_CONTROL, INPUT_MODE_PASSTHROUGH

        uint8_t vel_data[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        float vel = speed / this->mPerTick;
        std::memcpy(vel_data, &vel, 4);
        this->can->send(this->can_id + 0x00f, vel_data);

        uint8_t pos_data[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        float tick = std::max(std::min(target, maxPos), minPos) / this->mPerTick + this->tickOffset;
        std::memcpy(pos_data, &tick, 4);
        this->can->send(this->can_id + 0x00c, pos_data);
        this->state = MOVE;
    }

    void speed(float velocity)
    {
        this->setMode(8, 2, 2); // AXIS_STATE_CLOSED_LOOP_CONTROL, CONTROL_MODE_VELOCITY_CONTROL, INPUT_MODE_VEL_RAMP

        uint8_t data[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        float vel = velocity / this->mPerTick;
        std::memcpy(data, &vel, 4);
        this->can->send(this->can_id + 0x00d, data);
        float limit = fabs(vel * 2);
        std::memcpy(data, &limit, 4);
        this->can->send(this->can_id + 0x00f, data);
        this->state = MOVE;
    }

    void torque(float power)
    {
        this->setMode(8, 1, 1); // AXIS_STATE_CLOSED_LOOP_CONTROL, CONTROL_MODE_TORQUE_CONTROL, INPUT_MODE_PASSTHROUGH

        uint8_t data[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        std::memcpy(data, &power, 4);
        this->can->send(this->can_id + 0x00e, data);
        this->state = MOVE;
    }

    void home()
    {
        this->setMode(8, 2, 1); // AXIS_STATE_CLOSED_LOOP_CONTROL, CONTROL_MODE_VELOCITY_CONTROL, INPUT_MODE_PASSTHROUGH

        uint8_t data[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        float vel = this->homeSpeed / this->mPerTick;
        std::memcpy(data, &vel, 4);
        this->can->send(this->can_id + 0x00d, data);
        this->state = HOMING;
    }

    void stop()
    {
        this->setMode(1); // AXIS_STATE_IDLE

        this->state = this->is_home_active() ? HOME : STOP;
    }

    void setMode(uint8_t state, uint8_t controlMode=0, uint8_t inputMode=0)
    {
        if (this->odriveState.state != state)
        {
            this->can->send(this->can_id + 0x007, state, 0, 0, 0, 0, 0, 0, 0);
            this->odriveState.state = state;
        }
        if (this->odriveState.controlMode != controlMode ||
            this->odriveState.inputMode != inputMode)
        {
            this->can->send(this->can_id + 0x00b, controlMode, 0, 0, 0, inputMode, 0, 0, 0);
            this->odriveState.controlMode = controlMode;
            this->odriveState.inputMode = inputMode;
        }
    }

    bool is_home_active()
    {
        return this->home_switch != nullptr and this->home_switch->state == 0;
    }
};
