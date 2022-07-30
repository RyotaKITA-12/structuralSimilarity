from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
import pandas as pd


def main():
    var1 = function1()
    var2 = function2(var1)
    var3 = function3(var2)
    function4(var3, var2)


def function1():
    sample_data = load_diabetes()

    df = pd.DataFrame(
        data=sample_data.data,
        columns=sample_data.feature_names)
    df['Y'] = sample_data.target

    return df


def function2(var1):
    X = var1.drop('Y', axis=1).values
    y = var1['Y'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=0)
    data = {"train": {"X": X_train, "y": y_train},
            "test": {"X": X_test, "y": y_test}}

    return data


def function3(var1):
    args = {"alpha": 0.5}
    reg_model = Ridge(**args)
    reg_model.fit(var1["train"]["X"], var1["train"]["y"])

    return reg_model


def function4(var1, var2):
    preds = var1.predict(var2["test"]["X"])
    mse = mean_squared_error(preds, var2["test"]["y"])
    metrics = {"mse": mse}
    print(metrics)

    return


if __name__ == '__main__':
    main()
