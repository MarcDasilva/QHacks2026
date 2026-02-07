/*
  Control a simple Rive file using Data Binding. 

  Resourcs: 
  - Open the Rive file: https://rive.app/community/files/24637-46037-health-bar-data-binding-quick-start
  - Data Binding: https://rive.app/docs/runtimes/data-binding
*/

import React, { useEffect } from "react";
import {
  useRive,
  Layout,
  Fit,
  useViewModel,
  useViewModelInstance,
  useViewModelInstanceNumber,
  useViewModelInstanceTrigger,
} from "@rive-app/react-webgl2";
import "./styles.css";

export default function App() {
  const { rive, RiveComponent } = useRive({
    // Load a local riv `clean_the_car.riv` or upload your own!
    src: "quick_start_health_bar.riv",
    // Be sure to specify the correct state machine (or animation) name
    stateMachines: "State Machine 1",
    // This is optional.Provides additional layout control.
    layout: new Layout({
      fit: Fit.Layout, // Change to: rive.Fit.Contain, or Cover
      layoutScaleFactor: 1,
    }),
    // Autoplay the state machine
    autoplay: true,
    // This uses the view model instance defined in Rive
    autoBind: true,
  });

  const viewModel = useViewModel(rive, { name: "health_bar_01" });
  const vmi = useViewModelInstance(viewModel, { rive });

  const { value: health, setValue: setHealth } = useViewModelInstanceNumber(
    "health",
    vmi,
  );

  const { trigger: triggerGameOver } = useViewModelInstanceTrigger(
    "gameOver",
    vmi,
    {
      // Listen for the trigger getting fired from within Rive
      // Ex: When health is 0 and you click the `No` button
      onTrigger: () => {
        console.log("Trigger Fired!");
      },
    },
  );

  useEffect(() => {
    setHealth(10);
  }, [rive, setHealth]);

  return (
    <>
      <div className="rive-container">
        <RiveComponent />
      </div>
      <div className="demo-controls">
        <button
          onClick={() => {
            if (setHealth && health != null) {
              setHealth(health - 7);
            }
          }}
        >
          Take Damage
        </button>
        <button
          onClick={() => {
            if (setHealth) {
              setHealth(0);
            }
            if (triggerGameOver) {
              triggerGameOver();
            }
          }}
        >
          Game Over
        </button>
      </div>
    </>
  );
}
