import json
import requests
import pandas as pd

from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter

headers = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
    }

currency_rates = {}
shipping_to_IL = []
def get_product():
    product_id = input("Entere product-id:")
    return get_product_code(product_id)


def get_product_code(product_id):
    product_url = f"https://www.asos.com/search/?q={product_id}"
    page = requests.get(product_url, headers=headers)
    soup = BeautifulSoup(page.text, "html.parser").find("script", type="application/ld+json")
    product_data = json.loads(soup.string)

    return product_data["productID"]


def convert_currencies_to_usd(amount, old_currency):
    if old_currency in currency_rates:
        curr_to_usd = currency_rates[old_currency]
    else:
        curr_to_usd = CurrencyConverter().convert(amount=1, currency=old_currency, new_currency='USD')
        currency_rates[old_currency] = curr_to_usd

    return round(curr_to_usd * amount, 2)


def get_price(country_name, storeCode, product_code, currency):
    price_endpoint_url = f"https://www.asos.com/api/product/catalogue/v3/stockprice?productIds={product_code}&store={storeCode}&currency={currency}"

    try:
        price = requests.get(price_endpoint_url, headers=headers).json()[0]["productPrice"]["current"]["value"]
        return {"country_names": [country_name], "price": price,
                "price in usd": convert_currencies_to_usd(amount=price, old_currency=currency),
                "currency": currency}

    except IndexError:
        return None

    except ValueError:
        return None


def get_currencies(countries):
    for country in countries:
        api_url = f"https://www.asos.com/api/web/countrymetadata/v1/countrySelector/{country['countryCode']}" \
                  f"?keyStoreDataversion=ornjx7v-36&lang={country['defaultLanguage']}&platform=desktop"

        print(f"Getting {country['name']} currencies")
        response = requests.get(api_url)
        country['currencies'] = response.json()['data']['currencies']

# finding all the countries that ships to israel
def coutries_ship_to_israel(countries):
    cache = {}
    for country in countries:
        print(f"check if {country['name']} ships to israel...")

        api_url = f"https://www.asos.com/api/commerce/deliveryoptions/v2/deliverycountryoptions/?" \
                  f"country=IL&store={country['storeCode']}&lang={country['defaultLanguage']}&currency={country['currencies'][0]['currency']}"

        if api_url in cache:
            response = cache[api_url]
        else:
            response = requests.get(api_url).json()
            cache[api_url] = response

        if len(response['deliveryCountryOptions']) and country['name'] not in shipping_to_IL:
            shipping_to_IL.append(country['name'])


def main():
    f = open('countries.json', 'r')
    countries = json.load(f)
    f.close()

    get_currencies(countries=countries)
    coutries_ship_to_israel(countries=countries)
    print(shipping_to_IL)
    prices = []
    product_code = get_product()
    for country in countries:
        for currency in country['currencies']:
            price = get_price(country_name=country['name'], storeCode=country['storeCode'], product_code=product_code, currency=currency['currency'])
            if price:
                flag = True
                for idx, price2 in enumerate(prices):
                    if price2['price in usd'] == price['price in usd'] and price['currency'] == price2['currency']:
                        prices[idx]["country_names"].append(price["country_names"][0])
                        flag = False
                        break

                if flag:
                    prices.append(price)

    sorted_list = sorted(prices, key=lambda x: x['price in usd'])

    df1 = pd.DataFrame(sorted_list)
    df2 = pd.DataFrame(shipping_to_IL)
    writer = pd.ExcelWriter('result.xlsx', engine='xlsxwriter')

    df1.to_excel(writer, sheet_name='price of product')
    df2.to_excel(writer, sheet_name='countries shipping to Israel')
    writer.save()


if __name__ == "__main__":
    import sys

    sys.exit(main())



