MCT462 CURRENT GROUPED FP32 MODEL

MODEL ID: grouped_fp32_v1_d782992aeb8c
Recorded 2 HP development accuracy: 84.50% (698/826 windows).
Training accuracy: 83.53%.
2 HP balanced accuracy: 86.68%.
2 HP macro-F1: 0.8552.
Model file: baseline_fp32.tflite (2312 bytes), FP32, 140 parameters.
Training/fine-tuning source: baseline_fp32.keras.

IMPORTANT SCOPE
This is the latest model trained by the user in Colab and supplied as a saved run.
Packaging has not changed or retrained its weights. It uses 28 sources / 1621
training windows at 0 and 1 HP, and 14 sources / 826 development windows at 2 HP.
It includes outer-race positions 3:00, 6:00 and 12:00 and all three selected fault sizes.

The later Progress 1 data package proposes a DIFFERENT, fixed-6:00 subset. No model
has been trained on that revised subset and there is no new accuracy for it.
Do not call 84.50% a measurement on the revised 590-window validation set.
The existing model can support integration and optimization development as a
preliminary baseline; it has known difficult cases and is not a finished system.

FOR THE ESP32 TEAMMATE
Use baseline_fp32.tflite or the byte-identical C++ model_data.h. Include the matching
normalization.h and implement feature_contract.json in its exact feature order.
Input shape: [1,12], float32 normalized features. Output shape: [1,4] softmax scores.
The model does not accept a [1,2048] raw sample vector directly.
Class indices: 0 healthy, 1 inner_race, 2 outer_race, 3 ball.
PC sends raw 2048-sample windows prepared at 12 kHz; ESP32 extracts 12 features,
then applies (features - FEATURE_MEAN) / FEATURE_SCALE before inference.
Use feature_reference.py and raw_reference_PC_ONLY.npz to check feature/norm/score parity.
Keep ground truth, recording IDs, optimization data and all PC_ONLY artifacts on the PC.
Return a neutral window ID, model ID, class, confidence, feature time and inference time.
Actual ESP32 runtime compatibility and measurements remain to be checked on your board.

FOR THE OPTIMIZATION TEAMMATE
Start from baseline_fp32.keras with the included preprocessing. optimization_data_PC_ONLY.npz
contains normalized X_train/y_train and X_validation/y_validation. Those arrays are
already normalized: do not normalize them a second time. Use training data only for
fine-tuning and INT8 representative calibration. Keep 2 HP for development evaluation
and 3 HP reserved for final assessment. Do not treat validation samples as calibration data.
Keep each derived model with its own model ID, metrics and validation parity check.
Do not overwrite the original FP32 baseline. A smaller file is not a measured RAM saving.

FOR THE COMMUNICATION TEAMMATE
The raw_reference_PC_ONLY.npz includes all 826 raw development windows and matching
features, normalized inputs, labels, original-model scores and recording IDs.
Only raw samples plus neutral communication IDs should go to the ESP32; truth stays
on the PC. Regenerate/update expected predictions when changing the model version.
If the repository still contains an earlier 99.88% model or expected predictions,
do not combine them with this model's 84.50% metrics or preprocessing artifacts.
Keep firmware/reference code pointed to this explicit model version, and include
the model ID in returned results so PC evaluation can detect mismatched versions.

LOCAL REFERENCE CHECK
The original offline_verify.py checks raw-to-feature-to-model parity on the PC with
NumPy and ai-edge-litert installed. Run it from this directory:
    python offline_verify.py
It evaluates existing 2 HP development fixtures only. Its score is not new-data accuracy.
Record whether the network was disconnected if claiming an offline demonstration.
The Colab versions used for the saved run are in versions.json.

PROVENANCE
Original saved-run files, including historical HANDOFF.txt and frozen_model.json,
are preserved byte-for-byte. Their old note about missing subset requirements
predates the newly supplied Progress 1 checklist. Use MODEL_SUMMARY.json and this
README for the current handoff scope. Source-rate confirmation is still pending.
Package verification recomputed all 826 feature vectors and normalization, checked
saved score/label accuracy and original file hashes. It did not execute LiteRT anew
or claim an ESP32 run. The original export parity evidence is export_check.json.
