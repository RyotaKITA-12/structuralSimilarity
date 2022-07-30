from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
import pandas as pd


def main():
    df = function1()
    data = function2(df)
    reg_model = function3(data)
    function4(reg_model, data)


def function1():
    sample_data = load_diabetes()

    df = pd.DataFrame(
        data=sample_data.data,
        columns=sample_data.feature_names)
    df['Y'] = sample_data.target

    return df


def function2(df):
    X = df.drop('Y', axis=1).values
    y = df['Y'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=0)
    data = {"train": {"X": X_train, "y": y_train},
            "test": {"X": X_test, "y": y_test}}

    return data


def function3(data):
    args = {"alpha": 0.5}
    reg_model = Ridge(**args)
    reg_model.fit(data["train"]["X"], data["train"]["y"])

    return reg_model


def function4(reg_model, data):
    preds = reg_model.predict(data["test"]["X"])
    mse = mean_squared_error(preds, data["test"]["y"])
    metrics = {"mse": mse}
    print(metrics)

    return


if __name__ == '__main__':
    main()
